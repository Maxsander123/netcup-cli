#!/usr/bin/env python3
"""netbox-cli — Manage NetBox DCIM/IPAM/Virtualization from the terminal."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from urllib.parse import urlparse, parse_qs

import click
import requests
import urllib3
from rich.console import Console
from rich.table import Table
from rich import box
from rich.prompt import Confirm

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

VERSION    = "2.0.0"
CONFIG_DIR = Path.home() / ".config" / "netbox-cli"
CONFIG_FILE = CONFIG_DIR / "config.json"
CAPS_FILE   = CONFIG_DIR / "capabilities.json"

console = Console()

# Endpoints to probe for capability detection
_PROBE_ENDPOINTS = [
    ("devices",          "/api/dcim/devices/"),
    ("racks",            "/api/dcim/racks/"),
    ("interfaces",       "/api/dcim/interfaces/"),
    ("power-feeds",      "/api/dcim/power-feeds/"),
    ("power-panels",     "/api/dcim/power-panels/"),
    ("power-outlets",    "/api/dcim/power-outlets/"),
    ("power-ports",      "/api/dcim/power-ports/"),
    ("ip-addresses",     "/api/ipam/ip-addresses/"),
    ("prefixes",         "/api/ipam/prefixes/"),
    ("vlans",            "/api/ipam/vlans/"),
    ("virtual-machines", "/api/virtualization/virtual-machines/"),
    ("vm-interfaces",    "/api/virtualization/interfaces/"),
    ("clusters",         "/api/virtualization/clusters/"),
    ("contacts",         "/api/tenancy/contacts/"),
    ("tenants",          "/api/tenancy/tenants/"),
]


# ---------------------------------------------------------------------------
# Config / Auth
# ---------------------------------------------------------------------------

def load_config(require_auth: bool = True) -> dict:
    if not CONFIG_FILE.exists():
        if require_auth:
            console.print("[red]Not logged in.[/red] Run: netbox-cli login")
            sys.exit(1)
        return {}
    try:
        return json.loads(CONFIG_FILE.read_text())
    except (json.JSONDecodeError, OSError) as exc:
        console.print(f"[red]Config error:[/red] {exc}")
        sys.exit(1)


def save_config(data: dict) -> None:
    CONFIG_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
    tmp = CONFIG_DIR / ".config.tmp"
    fd = os.open(str(tmp), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        os.write(fd, json.dumps(data, indent=2).encode())
    finally:
        os.close(fd)
    tmp.replace(CONFIG_FILE)


def _base_url() -> str:
    return load_config()["url"].rstrip("/")


def _headers() -> dict:
    cfg = load_config()
    return {
        "Authorization": f"Token {cfg['token']}",
        "Accept":        "application/json",
        "Content-Type":  "application/json",
    }


# ---------------------------------------------------------------------------
# Capabilities / Permission probing
# ---------------------------------------------------------------------------

def probe_capabilities() -> dict:
    """Use OPTIONS requests to discover which HTTP methods are allowed per endpoint."""
    caps: dict = {}
    for key, path in _PROBE_ENDPOINTS:
        try:
            url = _base_url() + path
            r   = requests.options(url, headers=_headers(), verify=False, timeout=10)
            if r.ok:
                data    = r.json()
                actions = set(data.get("actions", {}).keys())
                # Fallback: if OPTIONS gives no actions, try a GET to confirm read access
                if not actions:
                    rg = requests.get(url, headers=_headers(), params={"limit": 1},
                                      verify=False, timeout=10)
                    actions = {"GET"} if rg.ok else set()
                caps[key] = sorted(actions)
            elif r.status_code == 403:
                caps[key] = []
            else:
                caps[key] = []
        except Exception:
            caps[key] = []
    return caps


def load_capabilities() -> dict:
    if not CAPS_FILE.exists():
        return {}
    try:
        return json.loads(CAPS_FILE.read_text())
    except Exception:
        return {}


def save_capabilities(caps: dict) -> None:
    CONFIG_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
    CAPS_FILE.write_text(json.dumps(caps, indent=2))


def _cap(key: str) -> list[str]:
    """Return allowed HTTP methods for an endpoint key (from cache)."""
    return load_capabilities().get(key, [])


def _can_read(key: str) -> bool:
    caps = _cap(key)
    return not caps or "GET" in caps   # empty caps = unchecked = assume allowed


def _can_write(key: str) -> bool:
    caps = _cap(key)
    if not caps:
        return True  # unchecked
    return "POST" in caps or "PUT" in caps or "PATCH" in caps


def _access_badge(actions: list[str]) -> str:
    if not actions:
        return "[red]✗ no access[/red]"
    has_write = bool({"POST", "PATCH", "PUT", "DELETE"} & set(actions))
    if has_write:
        return "[green]r/w[/green]"
    return "[yellow]r[/yellow]"


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

def _check(r: requests.Response) -> None:
    if not r.ok:
        if r.status_code == 403:
            console.print(
                f"[red]Permission denied (403)[/red] — "
                "run [bold]netbox-cli capabilities[/bold] to see your access level."
            )
        else:
            try:
                msg = r.json()
            except Exception:
                msg = r.text
            console.print(f"[red]API {r.status_code}:[/red] {msg}")
        sys.exit(1)


def api_get(path: str, params: dict | None = None) -> dict:
    url = _base_url() + path
    r   = requests.get(url, headers=_headers(), params=params, verify=False, timeout=30)
    _check(r)
    return r.json()


def api_post(path: str, body: dict | None = None) -> dict:
    url = _base_url() + path
    r   = requests.post(url, headers=_headers(), json=body or {}, verify=False, timeout=30)
    _check(r)
    return r.json() if r.content else {}


def api_patch(path: str, body: dict) -> dict:
    url = _base_url() + path
    r   = requests.patch(url, headers=_headers(), json=body, verify=False, timeout=30)
    _check(r)
    return r.json() if r.content else {}


def api_delete(path: str) -> None:
    url = _base_url() + path
    r   = requests.delete(url, headers=_headers(), verify=False, timeout=30)
    _check(r)


def api_get_all(path: str, params: dict | None = None) -> list[dict]:
    """Walk all NetBox pages and return the combined results list."""
    results: list[dict] = []
    p = dict(params or {})
    p.setdefault("limit", 200)
    p["offset"] = 0
    while True:
        data = api_get(path, params=p)
        results.extend(data.get("results", []))
        if not data.get("next"):
            break
        qs = parse_qs(urlparse(data["next"]).query)
        p["offset"] = int(qs.get("offset", [p["offset"] + p["limit"]])[0])
    return results


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _detail_table() -> tuple[Table, callable]:
    table = Table(box=box.SIMPLE, show_header=False, pad_edge=False)
    table.add_column("Key",   style="dim",  width=24)
    table.add_column("Value", style="bold")

    def row(k, v):
        table.add_row(k, str(v) if v is not None else "—")

    return table, row


def _cf(obj: dict, field: str, default: str = "—") -> str:
    return str((obj.get("custom_fields") or {}).get(field) or default)


def _nested(obj: dict | None, *keys: str, default: str = "—") -> str:
    for k in keys:
        if not isinstance(obj, dict):
            return default
        obj = obj.get(k)
    return str(obj) if obj is not None else default


def _status_color(status: str) -> str:
    return {
        "active":          "green",
        "planned":         "yellow",
        "staged":          "cyan",
        "failed":          "red",
        "decommissioning": "red",
        "inventory":       "dim",
        "offline":         "dim",
        "dhcp":            "blue",
        "slaac":           "blue",
        "connected":       "green",
        "planned":         "yellow",
    }.get((status or "").lower(), "dim")


def _colored_status(status: str) -> str:
    if not status:
        return "—"
    c = _status_color(status)
    return f"[{c}]{status}[/{c}]"


def _resolve_obj(endpoint: str, query: str, label: str) -> dict:
    """Resolve a named object by slug then full-text search."""
    results = api_get_all(endpoint, {"slug": query})
    if not results:
        results = api_get_all(endpoint, {"q": query})
    if len(results) == 1:
        return results[0]
    if len(results) > 1:
        exact = [x for x in results if x.get("name") == query or x.get("slug") == query]
        if len(exact) == 1:
            return exact[0]
        console.print(f"[red]Ambiguous {label}:[/red] '{query}' matches {len(results)} entries.")
        for x in results[:6]:
            console.print(f"  [dim]{x['id']}[/dim]  {x.get('name', '?')}")
        sys.exit(1)
    console.print(f"[red]{label} not found:[/red] {query}")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Object resolution helpers
# ---------------------------------------------------------------------------

def resolve_device(name_or_id: str) -> dict:
    if name_or_id.isdigit():
        return api_get(f"/api/dcim/devices/{name_or_id}/")
    results = api_get_all("/api/dcim/devices/", {"name": name_or_id})
    if len(results) == 1:
        return results[0]
    if len(results) > 1:
        exact = [d for d in results if d.get("name") == name_or_id]
        if len(exact) == 1:
            return exact[0]
    fallback = api_get_all("/api/dcim/devices/", {"q": name_or_id})
    if len(fallback) == 1:
        return fallback[0]
    if len(fallback) > 1:
        console.print(f"[red]Ambiguous:[/red] '{name_or_id}' matches {len(fallback)} devices.")
        for d in fallback[:8]:
            console.print(f"  [dim]{d['id']}[/dim]  {d.get('name', '?')}")
        sys.exit(1)
    console.print(f"[red]Device not found:[/red] {name_or_id}")
    sys.exit(1)


def resolve_vm(name_or_id: str) -> dict:
    if name_or_id.isdigit():
        return api_get(f"/api/virtualization/virtual-machines/{name_or_id}/")
    results = api_get_all("/api/virtualization/virtual-machines/", {"name": name_or_id})
    if len(results) == 1:
        return results[0]
    if len(results) > 1:
        exact = [v for v in results if v.get("name") == name_or_id]
        if len(exact) == 1:
            return exact[0]
    fallback = api_get_all("/api/virtualization/virtual-machines/", {"q": name_or_id})
    if len(fallback) == 1:
        return fallback[0]
    if len(fallback) > 1:
        console.print(f"[red]Ambiguous:[/red] '{name_or_id}' matches {len(fallback)} VMs.")
        for v in fallback[:8]:
            console.print(f"  [dim]{v['id']}[/dim]  {v.get('name', '?')}")
        sys.exit(1)
    console.print(f"[red]VM not found:[/red] {name_or_id}")
    sys.exit(1)


# ---------------------------------------------------------------------------
# CLI root
# ---------------------------------------------------------------------------

@click.group()
@click.version_option(VERSION, prog_name="netbox-cli")
def cli():
    """netbox-cli — Manage NetBox DCIM/IPAM/Virtualization from the terminal."""


# ---------------------------------------------------------------------------
# Auth commands
# ---------------------------------------------------------------------------

@cli.command("login")
def cmd_login():
    """Store NetBox URL and API token, then probe permissions."""
    console.print("Get a token at: [bold]NetBox → Admin → API Tokens[/bold]")
    url   = click.prompt("NetBox URL", default="https://netbox.internal.kaosozu-hosting.de")
    token = click.prompt("API token", hide_input=True)
    url   = url.rstrip("/").strip()
    token = token.strip()
    if not url or not token:
        console.print("[red]URL and token cannot be empty.[/red]")
        sys.exit(1)
    save_config({"url": url, "token": token})
    console.print("[green]✓[/green] Credentials saved. Testing connectivity…")
    try:
        data   = api_get("/api/status/")
        nb_ver = data.get("netbox-version", "?")
        console.print(f"[green]✓[/green] Connected to NetBox {nb_ver}.")
        console.print("[dim]Probing permissions…[/dim]")
        caps = probe_capabilities()
        save_capabilities(caps)
        rw_count = sum(1 for v in caps.values() if "POST" in v or "PATCH" in v)
        ro_count = sum(1 for v in caps.values() if v and "POST" not in v and "PATCH" not in v)
        no_count = sum(1 for v in caps.values() if not v)
        console.print(
            f"[green]✓[/green] Permissions cached: "
            f"[green]{rw_count} r/w[/green]  [yellow]{ro_count} r[/yellow]  [red]{no_count} denied[/red]  "
            f"— run [bold]netbox-cli capabilities[/bold] for details."
        )
    except SystemExit:
        console.print("[yellow]Warning:[/yellow] Could not verify — credentials saved anyway.")


@cli.command("logout")
def cmd_logout():
    """Remove stored credentials and cached capabilities."""
    if CONFIG_FILE.exists():
        CONFIG_FILE.unlink()
        console.print("[green]✓[/green] Logged out.")
    else:
        console.print("Not logged in.")
    if CAPS_FILE.exists():
        CAPS_FILE.unlink()


@cli.command("status")
def cmd_status():
    """Show authentication, connectivity, and permission summary."""
    cfg = load_config(require_auth=False)
    if not cfg.get("token"):
        console.print("[red]Not logged in.[/red]")
        return
    tok    = cfg["token"]
    masked = tok[:8] + "…" + tok[-4:] if len(tok) > 12 else "****"
    console.print(f"URL:   [bold]{cfg.get('url', '—')}[/bold]")
    console.print(f"Token: [dim]{masked}[/dim]")
    try:
        data   = api_get("/api/status/")
        nb_ver = data.get("netbox-version", "?")
        py_ver = data.get("python-version", "?")
        console.print(f"[green]✓[/green] NetBox [bold]{nb_ver}[/bold] (Python {py_ver}) — reachable.")
    except SystemExit:
        console.print("[red]✗[/red] API unreachable or token invalid.")
        return
    caps = load_capabilities()
    if caps:
        rw = sum(1 for v in caps.values() if "POST" in v or "PATCH" in v)
        ro = sum(1 for v in caps.values() if v and "POST" not in v and "PATCH" not in v)
        nd = sum(1 for v in caps.values() if not v)
        console.print(
            f"Perms: [green]{rw} r/w[/green]  [yellow]{ro} r[/yellow]  [red]{nd} denied[/red]  "
            f"[dim](netbox-cli capabilities for details)[/dim]"
        )
    else:
        console.print("[dim]Permissions: not probed yet — run 'netbox-cli capabilities'[/dim]")


@cli.command("capabilities")
def cmd_capabilities():
    """Probe and display per-endpoint permissions."""
    console.print("[dim]Probing permissions (this takes a few seconds)…[/dim]")
    caps = probe_capabilities()
    save_capabilities(caps)
    table = Table(box=box.SIMPLE, pad_edge=False, show_edge=False)
    table.add_column("Endpoint",    style="bold", no_wrap=True)
    table.add_column("Access",      no_wrap=True)
    table.add_column("Methods",     style="dim",  no_wrap=True)
    for key, path in _PROBE_ENDPOINTS:
        actions = caps.get(key, [])
        table.add_row(key, _access_badge(actions), " ".join(actions) or "—")
    console.print(table)


# ---------------------------------------------------------------------------
# device group
# ---------------------------------------------------------------------------

@cli.group("device")
def grp_device():
    """Manage physical devices (DCIM)."""


@grp_device.command("list")
@click.option("--role",   default=None, help="Filter by device role (slug or name)")
@click.option("--owner",  default=None, help="Filter by custom field owner")
@click.option("--site",   default=None, help="Filter by site slug or name")
@click.option("--rack",   default=None, help="Filter by rack name")
@click.option("--status", default=None, help="Filter by status (active, planned, …)")
@click.option("--json",   "as_json", is_flag=True)
def device_list(role, owner, site, rack, status, as_json):
    """List devices."""
    params: dict = {}
    if role:   params["role"]     = role
    if owner:  params["cf_owner"] = owner
    if site:   params["site"]     = site
    if rack:   params["rack"]     = rack
    if status: params["status"]   = status
    devices = api_get_all("/api/dcim/devices/", params)
    if as_json:
        click.echo(json.dumps(devices, indent=2))
        return
    table = Table(box=box.SIMPLE, pad_edge=False, show_edge=False)
    table.add_column("ID",     style="dim",     no_wrap=True, justify="right", width=6)
    table.add_column("Name",   style="bold",    no_wrap=True)
    table.add_column("Role",   style="cyan",    no_wrap=True)
    table.add_column("Type",   style="dim",     no_wrap=True)
    table.add_column("Site",   style="dim",     no_wrap=True)
    table.add_column("Rack/U",                  no_wrap=True, justify="right")
    table.add_column("Status",                  no_wrap=True)
    table.add_column("Owner",  style="magenta", no_wrap=True)
    for d in devices:
        role_name = _nested(d.get("role") or d.get("device_role"), "name")
        rack_obj  = d.get("rack")
        rack_name = _nested(rack_obj, "name")
        pos       = d.get("position")
        rack_u    = f"{rack_name} U{pos}" if rack_name != "—" and pos else rack_name
        table.add_row(
            str(d["id"]),
            d.get("name") or "—",
            role_name,
            _nested(d.get("device_type"), "display"),
            _nested(d.get("site"), "name"),
            rack_u,
            _colored_status(_nested(d.get("status"), "value")),
            _cf(d, "owner"),
        )
    console.print(table)
    console.print(f"[dim]{len(devices)} device(s)[/dim]")


@grp_device.command("info")
@click.argument("device")
@click.option("--json", "as_json", is_flag=True)
def device_info(device, as_json):
    """Show details for DEVICE (name or ID)."""
    d = resolve_device(device)
    if as_json:
        click.echo(json.dumps(d, indent=2))
        return
    table, row = _detail_table()
    row("ID",           d["id"])
    row("Name",         d.get("name"))
    row("Display",      d.get("display"))
    role = d.get("role") or d.get("device_role")
    row("Role",         _nested(role, "name"))
    row("Type",         _nested(d.get("device_type"), "display"))
    row("Manufacturer", _nested(d.get("device_type"), "manufacturer", "name"))
    row("Site",         _nested(d.get("site"), "name"))
    row("Rack",         _nested(d.get("rack"), "name"))
    row("Position",     d.get("position"))
    row("Face",         _nested(d.get("face"), "label"))
    row("Status",       _nested(d.get("status"), "value"))
    row("Platform",     _nested(d.get("platform"), "name"))
    row("Serial",       d.get("serial") or "—")
    row("Asset Tag",    d.get("asset_tag") or "—")
    row("Tenant",       _nested(d.get("tenant"), "name"))
    row("Owner",        _cf(d, "owner"))
    row("Comments",     (d.get("comments") or "").strip() or "—")
    row("Created",      d.get("created"))
    row("Last Updated", d.get("last_updated"))
    console.print(table)


@grp_device.command("search")
@click.argument("query")
def device_search(query):
    """Full-text search for devices matching QUERY."""
    devices = api_get_all("/api/dcim/devices/", {"q": query})
    if not devices:
        console.print(f"[dim]No devices found for:[/dim] {query}")
        return
    table = Table(box=box.SIMPLE, pad_edge=False, show_edge=False)
    table.add_column("ID",    style="dim",     no_wrap=True, justify="right", width=6)
    table.add_column("Name",  style="bold",    no_wrap=True)
    table.add_column("Role",  style="cyan",    no_wrap=True)
    table.add_column("Site",  style="dim",     no_wrap=True)
    table.add_column("Status",                 no_wrap=True)
    table.add_column("Owner", style="magenta", no_wrap=True)
    for d in devices:
        table.add_row(
            str(d["id"]),
            d.get("name") or "—",
            _nested(d.get("role") or d.get("device_role"), "name"),
            _nested(d.get("site"), "name"),
            _colored_status(_nested(d.get("status"), "value")),
            _cf(d, "owner"),
        )
    console.print(table)
    console.print(f"[dim]{len(devices)} result(s)[/dim]")


@grp_device.command("create")
@click.option("--name",   required=True)
@click.option("--type",   "dtype", required=True, help="Device type name or ID")
@click.option("--role",   required=True, help="Device role slug or name")
@click.option("--site",   required=True, help="Site slug or name")
@click.option("--rack",   default=None)
@click.option("--owner",  default=None)
@click.option("--status", default="active", show_default=True)
def device_create(name, dtype, role, site, rack, owner, status):
    """Create a new device."""
    role_obj = _resolve_obj("/api/dcim/device-roles/", role, "Role")
    if dtype.isdigit():
        dtype_obj = api_get(f"/api/dcim/device-types/{dtype}/")
    else:
        results   = api_get_all("/api/dcim/device-types/", {"q": dtype})
        if not results:
            console.print(f"[red]Device type not found:[/red] {dtype}")
            sys.exit(1)
        exact     = [x for x in results if x.get("display") == dtype or x.get("model") == dtype]
        dtype_obj = exact[0] if exact else results[0]
    site_obj = _resolve_obj("/api/dcim/sites/", site, "Site")
    body: dict = {
        "name": name, "device_type": dtype_obj["id"],
        "role": role_obj["id"], "site": site_obj["id"], "status": status,
    }
    if rack:
        rs = api_get_all("/api/dcim/racks/", {"name": rack})
        if not rs:
            console.print(f"[red]Rack not found:[/red] {rack}")
            sys.exit(1)
        body["rack"] = rs[0]["id"]
    if owner:
        body["custom_fields"] = {"owner": owner}
    d = api_post("/api/dcim/devices/", body)
    console.print(f"[green]✓[/green] Created device [bold]{d.get('name')}[/bold] (ID: {d['id']})")


@grp_device.command("delete")
@click.argument("device")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation")
def device_delete(device, yes):
    """Delete DEVICE (with confirmation)."""
    d = resolve_device(device)
    if not yes:
        if not Confirm.ask(f"Delete device [bold]{d.get('name')}[/bold] (ID: {d['id']})?"):
            console.print("Aborted.")
            return
    api_delete(f"/api/dcim/devices/{d['id']}/")
    console.print(f"[green]✓[/green] Deleted device [bold]{d.get('name')}[/bold].")


@grp_device.command("set-owner")
@click.argument("device")
@click.argument("owner")
def device_set_owner(device, owner):
    """Set the owner custom field on DEVICE. Empty string clears it."""
    d   = resolve_device(device)
    val = owner if owner else None
    api_patch(f"/api/dcim/devices/{d['id']}/", {"custom_fields": {"owner": val}})
    console.print(f"[green]✓[/green] Owner of [bold]{d.get('name')}[/bold] → {val or '(cleared)'}")


@grp_device.command("set-status")
@click.argument("device")
@click.argument("status", type=click.Choice(
    ["active", "planned", "staged", "failed", "decommissioning", "inventory", "offline"],
    case_sensitive=False,
))
def device_set_status(device, status):
    """Set the status of DEVICE."""
    d = resolve_device(device)
    api_patch(f"/api/dcim/devices/{d['id']}/", {"status": status})
    console.print(f"[green]✓[/green] Status of [bold]{d.get('name')}[/bold] → {_colored_status(status)}")


@grp_device.command("interfaces")
@click.argument("device")
@click.option("--json", "as_json", is_flag=True)
def device_interfaces(device, as_json):
    """List interfaces on DEVICE."""
    d      = resolve_device(device)
    ifaces = api_get_all("/api/dcim/interfaces/", {"device_id": d["id"]})
    if as_json:
        click.echo(json.dumps(ifaces, indent=2))
        return
    table = Table(box=box.SIMPLE, pad_edge=False, show_edge=False)
    table.add_column("ID",      style="dim",   no_wrap=True, justify="right", width=6)
    table.add_column("Name",    style="bold",  no_wrap=True)
    table.add_column("Type",    style="dim",   no_wrap=True)
    table.add_column("Speed",                  no_wrap=True, justify="right")
    table.add_column("MAC",     style="dim",   no_wrap=True)
    table.add_column("Enabled",                no_wrap=True)
    table.add_column("IP count",               no_wrap=True, justify="right")
    for iface in ifaces:
        speed = iface.get("speed")
        speed_str = f"{speed // 1000}G" if speed and speed >= 1000 else (f"{speed}M" if speed else "—")
        enabled   = "[green]✓[/green]" if iface.get("enabled") else "[red]✗[/red]"
        ip_count  = str(iface.get("count_ipaddresses", 0))
        table.add_row(
            str(iface["id"]),
            iface.get("name") or "—",
            _nested(iface.get("type"), "label"),
            speed_str,
            iface.get("mac_address") or "—",
            enabled,
            ip_count,
        )
    console.print(f"\n[bold]{d.get('name')}[/bold] — interfaces\n")
    console.print(table)
    console.print(f"[dim]{len(ifaces)} interface(s)[/dim]")


# ---------------------------------------------------------------------------
# vm group
# ---------------------------------------------------------------------------

@cli.group("vm")
def grp_vm():
    """Manage virtual machines (Virtualization)."""


@grp_vm.command("list")
@click.option("--cluster", default=None, help="Filter by cluster name")
@click.option("--role",    default=None, help="Filter by VM role")
@click.option("--owner",   default=None, help="Filter by custom field owner")
@click.option("--status",  default=None, help="Filter by status")
@click.option("--json",    "as_json", is_flag=True)
def vm_list(cluster, role, owner, status, as_json):
    """List virtual machines."""
    params: dict = {}
    if cluster: params["cluster"] = cluster
    if role:    params["role"]    = role
    if owner:   params["cf_owner"] = owner
    if status:  params["status"]  = status
    vms = api_get_all("/api/virtualization/virtual-machines/", params)
    if as_json:
        click.echo(json.dumps(vms, indent=2))
        return
    table = Table(box=box.SIMPLE, pad_edge=False, show_edge=False)
    table.add_column("ID",      style="dim",     no_wrap=True, justify="right", width=6)
    table.add_column("Name",    style="bold",    no_wrap=True)
    table.add_column("Cluster", style="cyan",    no_wrap=True)
    table.add_column("Role",    style="dim",     no_wrap=True)
    table.add_column("vCPUs",                    no_wrap=True, justify="right")
    table.add_column("RAM",                      no_wrap=True, justify="right")
    table.add_column("Disk",                     no_wrap=True, justify="right")
    table.add_column("Status",                   no_wrap=True)
    table.add_column("Owner",   style="magenta", no_wrap=True)
    for v in vms:
        vcpus = str(v.get("vcpus") or "—")
        ram   = f"{v.get('memory') // 1024}G" if v.get("memory") else "—"
        disk  = f"{v.get('disk')}G" if v.get("disk") else "—"
        table.add_row(
            str(v["id"]),
            v.get("name") or "—",
            _nested(v.get("cluster"), "name"),
            _nested(v.get("role"), "name"),
            vcpus,
            ram,
            disk,
            _colored_status(_nested(v.get("status"), "value")),
            _cf(v, "owner"),
        )
    console.print(table)
    console.print(f"[dim]{len(vms)} VM(s)[/dim]")


@grp_vm.command("info")
@click.argument("vm")
@click.option("--json", "as_json", is_flag=True)
def vm_info(vm, as_json):
    """Show details for VM (name or ID)."""
    v = resolve_vm(vm)
    if as_json:
        click.echo(json.dumps(v, indent=2))
        return
    table, row = _detail_table()
    row("ID",           v["id"])
    row("Name",         v.get("name"))
    row("Cluster",      _nested(v.get("cluster"), "name"))
    row("Site",         _nested(v.get("site"), "name"))
    row("Role",         _nested(v.get("role"), "name"))
    row("Status",       _nested(v.get("status"), "value"))
    row("Platform",     _nested(v.get("platform"), "name"))
    row("vCPUs",        v.get("vcpus"))
    ram = v.get("memory")
    row("RAM",          f"{ram // 1024}G ({ram} MB)" if ram else "—")
    row("Disk",         f"{v.get('disk')}G" if v.get("disk") else "—")
    row("Primary IPv4", _nested(v.get("primary_ip4"), "address"))
    row("Primary IPv6", _nested(v.get("primary_ip6"), "address"))
    row("Tenant",       _nested(v.get("tenant"), "name"))
    row("Owner",        _cf(v, "owner"))
    row("Comments",     (v.get("comments") or "").strip() or "—")
    row("Created",      v.get("created"))
    row("Last Updated", v.get("last_updated"))
    console.print(table)


@grp_vm.command("search")
@click.argument("query")
def vm_search(query):
    """Full-text search for VMs matching QUERY."""
    vms = api_get_all("/api/virtualization/virtual-machines/", {"q": query})
    if not vms:
        console.print(f"[dim]No VMs found for:[/dim] {query}")
        return
    table = Table(box=box.SIMPLE, pad_edge=False, show_edge=False)
    table.add_column("ID",      style="dim",     no_wrap=True, justify="right", width=6)
    table.add_column("Name",    style="bold",    no_wrap=True)
    table.add_column("Cluster", style="cyan",    no_wrap=True)
    table.add_column("Status",                   no_wrap=True)
    table.add_column("Owner",   style="magenta", no_wrap=True)
    for v in vms:
        table.add_row(
            str(v["id"]),
            v.get("name") or "—",
            _nested(v.get("cluster"), "name"),
            _colored_status(_nested(v.get("status"), "value")),
            _cf(v, "owner"),
        )
    console.print(table)
    console.print(f"[dim]{len(vms)} result(s)[/dim]")


@grp_vm.command("create")
@click.option("--name",    required=True)
@click.option("--cluster", required=True, help="Cluster name")
@click.option("--role",    default=None,  help="VM role slug or name")
@click.option("--vcpus",   default=None,  type=float)
@click.option("--ram",     default=None,  type=int, help="RAM in MB")
@click.option("--disk",    default=None,  type=int, help="Disk in GB")
@click.option("--owner",   default=None)
@click.option("--status",  default="active", show_default=True)
def vm_create(name, cluster, role, vcpus, ram, disk, owner, status):
    """Create a new VM."""
    cluster_obj = _resolve_obj("/api/virtualization/clusters/", cluster, "Cluster")
    body: dict  = {"name": name, "cluster": cluster_obj["id"], "status": status}
    if role:
        role_obj     = _resolve_obj("/api/dcim/device-roles/", role, "Role")
        body["role"] = role_obj["id"]
    if vcpus is not None: body["vcpus"]  = vcpus
    if ram   is not None: body["memory"] = ram
    if disk  is not None: body["disk"]   = disk
    if owner:             body["custom_fields"] = {"owner": owner}
    v = api_post("/api/virtualization/virtual-machines/", body)
    console.print(f"[green]✓[/green] Created VM [bold]{v.get('name')}[/bold] (ID: {v['id']})")


@grp_vm.command("delete")
@click.argument("vm")
@click.option("--yes", "-y", is_flag=True)
def vm_delete(vm, yes):
    """Delete VM (with confirmation)."""
    v = resolve_vm(vm)
    if not yes:
        if not Confirm.ask(f"Delete VM [bold]{v.get('name')}[/bold] (ID: {v['id']})?"):
            console.print("Aborted.")
            return
    api_delete(f"/api/virtualization/virtual-machines/{v['id']}/")
    console.print(f"[green]✓[/green] Deleted VM [bold]{v.get('name')}[/bold].")


@grp_vm.command("set-status")
@click.argument("vm")
@click.argument("status", type=click.Choice(
    ["active", "planned", "staged", "failed", "decommissioning", "offline"],
    case_sensitive=False,
))
def vm_set_status(vm, status):
    """Set the status of VM."""
    v = resolve_vm(vm)
    api_patch(f"/api/virtualization/virtual-machines/{v['id']}/", {"status": status})
    console.print(f"[green]✓[/green] Status of [bold]{v.get('name')}[/bold] → {_colored_status(status)}")


@grp_vm.command("interfaces")
@click.argument("vm")
@click.option("--json", "as_json", is_flag=True)
def vm_interfaces(vm, as_json):
    """List interfaces on VM."""
    v      = resolve_vm(vm)
    ifaces = api_get_all("/api/virtualization/interfaces/", {"virtual_machine_id": v["id"]})
    if as_json:
        click.echo(json.dumps(ifaces, indent=2))
        return
    table = Table(box=box.SIMPLE, pad_edge=False, show_edge=False)
    table.add_column("ID",    style="dim",  no_wrap=True, justify="right", width=6)
    table.add_column("Name",  style="bold", no_wrap=True)
    table.add_column("MAC",   style="dim",  no_wrap=True)
    table.add_column("Enabled",             no_wrap=True)
    table.add_column("IP count",            no_wrap=True, justify="right")
    for iface in ifaces:
        enabled = "[green]✓[/green]" if iface.get("enabled") else "[red]✗[/red]"
        table.add_row(
            str(iface["id"]),
            iface.get("name") or "—",
            iface.get("mac_address") or "—",
            enabled,
            str(iface.get("count_ipaddresses", 0)),
        )
    console.print(f"\n[bold]{v.get('name')}[/bold] — interfaces\n")
    console.print(table)
    console.print(f"[dim]{len(ifaces)} interface(s)[/dim]")


@grp_vm.command("clusters")
@click.option("--json", "as_json", is_flag=True)
def vm_clusters(as_json):
    """List VM clusters."""
    clusters = api_get_all("/api/virtualization/clusters/")
    if as_json:
        click.echo(json.dumps(clusters, indent=2))
        return
    table = Table(box=box.SIMPLE, pad_edge=False, show_edge=False)
    table.add_column("ID",   style="dim",  no_wrap=True, justify="right", width=6)
    table.add_column("Name", style="bold", no_wrap=True)
    table.add_column("Type", style="dim",  no_wrap=True)
    table.add_column("Site", style="dim",  no_wrap=True)
    table.add_column("VMs",               no_wrap=True, justify="right")
    for c in clusters:
        table.add_row(
            str(c["id"]),
            c.get("name") or "—",
            _nested(c.get("type"), "name"),
            _nested(c.get("site"), "name"),
            str(c.get("device_count", 0) + c.get("virtualmachine_count", 0)),
        )
    console.print(table)
    console.print(f"[dim]{len(clusters)} cluster(s)[/dim]")


# ---------------------------------------------------------------------------
# power group
# ---------------------------------------------------------------------------

@cli.group("power")
def grp_power():
    """Manage power infrastructure (DCIM)."""


@grp_power.command("feeds")
@click.option("--rack", default=None, help="Filter by rack name")
@click.option("--json", "as_json", is_flag=True)
def power_feeds(rack, as_json):
    """List power feeds."""
    params: dict = {}
    if rack:
        rs = api_get_all("/api/dcim/racks/", {"name": rack})
        if rs:
            params["rack_id"] = rs[0]["id"]
    feeds = api_get_all("/api/dcim/power-feeds/", params)
    if as_json:
        click.echo(json.dumps(feeds, indent=2))
        return
    table = Table(box=box.SIMPLE, pad_edge=False, show_edge=False)
    table.add_column("ID",      style="dim",  no_wrap=True, justify="right", width=6)
    table.add_column("Name",    style="bold", no_wrap=True)
    table.add_column("Panel",   style="dim",  no_wrap=True)
    table.add_column("Rack",    style="dim",  no_wrap=True)
    table.add_column("Type",    style="dim",  no_wrap=True)
    table.add_column("Voltage",               no_wrap=True, justify="right")
    table.add_column("Amperage",              no_wrap=True, justify="right")
    table.add_column("Status",                no_wrap=True)
    for f in feeds:
        table.add_row(
            str(f["id"]),
            f.get("name") or "—",
            _nested(f.get("power_panel"), "name"),
            _nested(f.get("rack"), "name"),
            _nested(f.get("type"), "label"),
            f"{f.get('voltage', '—')}V" if f.get("voltage") else "—",
            f"{f.get('amperage', '—')}A" if f.get("amperage") else "—",
            _colored_status(_nested(f.get("status"), "value")),
        )
    console.print(table)
    console.print(f"[dim]{len(feeds)} feed(s)[/dim]")


@grp_power.command("panels")
@click.option("--json", "as_json", is_flag=True)
def power_panels(as_json):
    """List power panels."""
    panels = api_get_all("/api/dcim/power-panels/")
    if as_json:
        click.echo(json.dumps(panels, indent=2))
        return
    table = Table(box=box.SIMPLE, pad_edge=False, show_edge=False)
    table.add_column("ID",   style="dim",  no_wrap=True, justify="right", width=6)
    table.add_column("Name", style="bold", no_wrap=True)
    table.add_column("Site", style="dim",  no_wrap=True)
    table.add_column("Rack", style="dim",  no_wrap=True)
    table.add_column("Feeds",              no_wrap=True, justify="right")
    for p in panels:
        table.add_row(
            str(p["id"]),
            p.get("name") or "—",
            _nested(p.get("site"), "name"),
            _nested(p.get("rack"), "name"),
            str(p.get("powerfeed_count", "—")),
        )
    console.print(table)
    console.print(f"[dim]{len(panels)} panel(s)[/dim]")


@grp_power.command("ports")
@click.argument("device")
@click.option("--json", "as_json", is_flag=True)
def power_ports(device, as_json):
    """List power ports (consumers) on DEVICE."""
    d     = resolve_device(device)
    ports = api_get_all("/api/dcim/power-ports/", {"device_id": d["id"]})
    if as_json:
        click.echo(json.dumps(ports, indent=2))
        return
    table = Table(box=box.SIMPLE, pad_edge=False, show_edge=False)
    table.add_column("ID",            style="dim",   no_wrap=True, justify="right", width=6)
    table.add_column("Name",          style="bold",  no_wrap=True)
    table.add_column("Type",          style="dim",   no_wrap=True)
    table.add_column("Max draw (W)",                 no_wrap=True, justify="right")
    table.add_column("Alloc draw (W)",               no_wrap=True, justify="right")
    table.add_column("Connected to",  style="dim",   no_wrap=True)
    for p in ports:
        connected = (p.get("connected_endpoints") or [{}])[0].get("display", "—") if p.get("connected_endpoints") else "—"
        table.add_row(
            str(p["id"]),
            p.get("name") or "—",
            _nested(p.get("type"), "label"),
            str(p.get("maximum_draw") or "—"),
            str(p.get("allocated_draw") or "—"),
            connected,
        )
    console.print(f"\n[bold]{d.get('name')}[/bold] — power ports\n")
    console.print(table)
    console.print(f"[dim]{len(ports)} port(s)[/dim]")


@grp_power.command("outlets")
@click.argument("device")
@click.option("--json", "as_json", is_flag=True)
def power_outlets(device, as_json):
    """List power outlets (sources) on DEVICE (e.g. PDUs)."""
    d       = resolve_device(device)
    outlets = api_get_all("/api/dcim/power-outlets/", {"device_id": d["id"]})
    if as_json:
        click.echo(json.dumps(outlets, indent=2))
        return
    table = Table(box=box.SIMPLE, pad_edge=False, show_edge=False)
    table.add_column("ID",           style="dim",  no_wrap=True, justify="right", width=6)
    table.add_column("Name",         style="bold", no_wrap=True)
    table.add_column("Type",         style="dim",  no_wrap=True)
    table.add_column("Feed leg",     style="dim",  no_wrap=True)
    table.add_column("Connected to", style="dim",  no_wrap=True)
    for o in outlets:
        connected = (o.get("connected_endpoints") or [{}])[0].get("display", "—") if o.get("connected_endpoints") else "—"
        table.add_row(
            str(o["id"]),
            o.get("name") or "—",
            _nested(o.get("type"), "label"),
            _nested(o.get("feed_leg"), "label"),
            connected,
        )
    console.print(f"\n[bold]{d.get('name')}[/bold] — power outlets\n")
    console.print(table)
    console.print(f"[dim]{len(outlets)} outlet(s)[/dim]")


# ---------------------------------------------------------------------------
# ip group
# ---------------------------------------------------------------------------

@cli.group("ip")
def grp_ip():
    """Manage IP addresses (IPAM)."""


@grp_ip.command("list")
@click.option("--device", default=None)
@click.option("--prefix", default=None, help="Filter by parent prefix (e.g. 10.0.0.0/24)")
@click.option("--free",   is_flag=True,  help="Show only unassigned IPs")
@click.option("--json",   "as_json", is_flag=True)
def ip_list(device, prefix, free, as_json):
    """List IP addresses."""
    params: dict = {}
    if device:
        dev = resolve_device(device)
        params["device_id"] = dev["id"]
    if prefix: params["parent"] = prefix
    if free:   params["assigned_object_id__isnull"] = "true"
    ips = api_get_all("/api/ipam/ip-addresses/", params)
    if as_json:
        click.echo(json.dumps(ips, indent=2))
        return
    table = Table(box=box.SIMPLE, pad_edge=False, show_edge=False)
    table.add_column("ID",          style="dim",   no_wrap=True, justify="right", width=6)
    table.add_column("Address",     style="green", no_wrap=True)
    table.add_column("VRF",         style="dim",   no_wrap=True)
    table.add_column("Status",                     no_wrap=True)
    table.add_column("DNS Name",    style="dim",   no_wrap=True)
    table.add_column("Assigned to",               no_wrap=True)
    for ip in ips:
        assigned = (ip.get("assigned_object") or {}).get("display") or "—"
        table.add_row(
            str(ip["id"]),
            ip.get("address", "—"),
            _nested(ip.get("vrf"), "name"),
            _colored_status(_nested(ip.get("status"), "value")),
            ip.get("dns_name") or "—",
            assigned,
        )
    console.print(table)
    console.print(f"[dim]{len(ips)} address(es)[/dim]")


@grp_ip.command("info")
@click.argument("address")
def ip_info(address):
    """Show details for an IP ADDRESS."""
    results = api_get_all("/api/ipam/ip-addresses/", {"address": address})
    if not results:
        console.print(f"[red]IP not found:[/red] {address}")
        sys.exit(1)
    ip = results[0]
    table, row = _detail_table()
    row("ID",           ip["id"])
    row("Address",      ip.get("address"))
    row("VRF",          _nested(ip.get("vrf"), "name"))
    row("Status",       _nested(ip.get("status"), "value"))
    row("Role",         _nested(ip.get("role"), "value"))
    row("DNS Name",     ip.get("dns_name") or "—")
    row("Description",  ip.get("description") or "—")
    row("Assigned to",  (ip.get("assigned_object") or {}).get("display") or "—")
    row("Tenant",       _nested(ip.get("tenant"), "name"))
    row("Created",      ip.get("created"))
    row("Last Updated", ip.get("last_updated"))
    console.print(table)


@grp_ip.command("create")
@click.argument("address", metavar="ADDRESS", help="IP address with prefix length (e.g. 10.0.0.5/24)")
@click.option("--dns-name",    default="", help="DNS name")
@click.option("--description", default="", help="Description")
@click.option("--status",      default="active", show_default=True,
              type=click.Choice(["active", "reserved", "deprecated", "dhcp", "slaac"]))
def ip_create(address, dns_name, description, status):
    """Create a new IP address."""
    body = {"address": address, "status": status}
    if dns_name:    body["dns_name"]    = dns_name
    if description: body["description"] = description
    ip = api_post("/api/ipam/ip-addresses/", body)
    console.print(f"[green]✓[/green] Created IP [bold]{ip.get('address')}[/bold] (ID: {ip['id']})")


@grp_ip.command("delete")
@click.argument("address")
@click.option("--yes", "-y", is_flag=True)
def ip_delete(address, yes):
    """Delete an IP ADDRESS (with confirmation)."""
    results = api_get_all("/api/ipam/ip-addresses/", {"address": address})
    if not results:
        console.print(f"[red]IP not found:[/red] {address}")
        sys.exit(1)
    ip = results[0]
    if not yes:
        if not Confirm.ask(f"Delete IP [bold]{ip.get('address')}[/bold] (ID: {ip['id']})?"):
            console.print("Aborted.")
            return
    api_delete(f"/api/ipam/ip-addresses/{ip['id']}/")
    console.print(f"[green]✓[/green] Deleted IP [bold]{address}[/bold].")


@grp_ip.command("assign")
@click.argument("address")
@click.option("--device",    required=True)
@click.option("--interface", required=True)
def ip_assign(address, device, interface):
    """Assign ADDRESS to an interface on DEVICE."""
    dev    = resolve_device(device)
    ifaces = api_get_all("/api/dcim/interfaces/", {"device_id": dev["id"], "name": interface})
    if not ifaces:
        console.print(f"[red]Interface not found:[/red] {interface} on {dev.get('name')}")
        sys.exit(1)
    body = {
        "assigned_object_type": "dcim.interface",
        "assigned_object_id":   ifaces[0]["id"],
    }
    existing = api_get_all("/api/ipam/ip-addresses/", {"address": address})
    if existing:
        api_patch(f"/api/ipam/ip-addresses/{existing[0]['id']}/", body)
        console.print(f"[green]✓[/green] Assigned [bold]{address}[/bold] → {dev.get('name')}/{interface}")
    else:
        body["address"] = address
        body["status"]  = "active"
        ip = api_post("/api/ipam/ip-addresses/", body)
        console.print(
            f"[green]✓[/green] Created and assigned [bold]{address}[/bold] → "
            f"{dev.get('name')}/{interface} (ID: {ip['id']})"
        )


# ---------------------------------------------------------------------------
# prefix group
# ---------------------------------------------------------------------------

@cli.group("prefix")
def grp_prefix():
    """Manage IP prefixes (IPAM)."""


@grp_prefix.command("list")
@click.option("--json", "as_json", is_flag=True)
def prefix_list(as_json):
    """List IP prefixes."""
    prefixes = api_get_all("/api/ipam/prefixes/")
    if as_json:
        click.echo(json.dumps(prefixes, indent=2))
        return
    table = Table(box=box.SIMPLE, pad_edge=False, show_edge=False)
    table.add_column("ID",     style="dim",   no_wrap=True, justify="right", width=6)
    table.add_column("Prefix", style="green", no_wrap=True)
    table.add_column("VRF",    style="dim",   no_wrap=True)
    table.add_column("Site",   style="dim",   no_wrap=True)
    table.add_column("Role",   style="cyan",  no_wrap=True)
    table.add_column("Status",               no_wrap=True)
    table.add_column("Desc",   style="dim",  no_wrap=True)
    for p in prefixes:
        table.add_row(
            str(p["id"]),
            p.get("prefix", "—"),
            _nested(p.get("vrf"),  "name"),
            _nested(p.get("site"), "name"),
            _nested(p.get("role"), "name"),
            _colored_status(_nested(p.get("status"), "value")),
            p.get("description") or "—",
        )
    console.print(table)
    console.print(f"[dim]{len(prefixes)} prefix(es)[/dim]")


# ---------------------------------------------------------------------------
# rack group
# ---------------------------------------------------------------------------

@cli.group("rack")
def grp_rack():
    """Manage racks (DCIM)."""


@grp_rack.command("list")
@click.option("--json", "as_json", is_flag=True)
def rack_list(as_json):
    """List racks."""
    racks = api_get_all("/api/dcim/racks/")
    if as_json:
        click.echo(json.dumps(racks, indent=2))
        return
    table = Table(box=box.SIMPLE, pad_edge=False, show_edge=False)
    table.add_column("ID",     style="dim",  no_wrap=True, justify="right", width=6)
    table.add_column("Name",   style="bold", no_wrap=True)
    table.add_column("Site",   style="dim",  no_wrap=True)
    table.add_column("Height",              no_wrap=True, justify="right")
    table.add_column("Tenant", style="dim", no_wrap=True)
    for r in racks:
        table.add_row(
            str(r["id"]),
            r.get("name") or "—",
            _nested(r.get("site"), "name"),
            f"{r.get('u_height', '?')}U",
            _nested(r.get("tenant"), "name"),
        )
    console.print(table)
    console.print(f"[dim]{len(racks)} rack(s)[/dim]")


@grp_rack.command("info")
@click.argument("name")
@click.option("--json", "as_json", is_flag=True)
def rack_info(name, as_json):
    """Show rack elevation for rack NAME."""
    racks = api_get_all("/api/dcim/racks/", {"name": name})
    if not racks:
        console.print(f"[red]Rack not found:[/red] {name}")
        sys.exit(1)
    rack     = racks[0]
    rack_id  = rack["id"]
    u_height = rack.get("u_height", 47)
    if as_json:
        click.echo(json.dumps(rack, indent=2))
        return
    devices = api_get_all("/api/dcim/devices/", {"rack_id": rack_id})
    occupied: dict[int, str] = {}
    for d in devices:
        pos    = d.get("position")
        uheigh = int((d.get("device_type") or {}).get("u_height") or 1)
        if pos is None:
            continue
        dev_name = d.get("name") or f"device-{d['id']}"
        for u in range(int(pos), int(pos) + uheigh):
            occupied[u] = dev_name
    used_u = len(occupied)
    free_u = u_height - used_u
    console.print(
        f"\n[bold]{rack.get('name')}[/bold]  "
        f"[dim]{_nested(rack.get('site'), 'name')}[/dim]  "
        f"{u_height}U rack\n"
    )
    table = Table(box=box.SIMPLE, show_header=False, pad_edge=False)
    table.add_column("U",      style="dim", width=4,  justify="right")
    table.add_column("Block",               width=3)
    table.add_column("Device",              no_wrap=True)
    prev = None
    for u in range(u_height, 0, -1):
        dev_name = occupied.get(u)
        if dev_name:
            label = dev_name if dev_name != prev else ""
            table.add_row(f"U{u}", "[blue]█[/blue]", label)
        else:
            table.add_row(f"U{u}", "[dim]·[/dim]", "")
        prev = dev_name
    console.print(table)
    console.print(
        f"[green]Used: {used_u}U[/green]  [dim]Free: {free_u}U[/dim]  Total: {u_height}U\n"
    )


# ---------------------------------------------------------------------------
# vlan group
# ---------------------------------------------------------------------------

@cli.group("vlan")
def grp_vlan():
    """Manage VLANs (IPAM)."""


@grp_vlan.command("list")
@click.option("--json", "as_json", is_flag=True)
def vlan_list(as_json):
    """List VLANs."""
    vlans = api_get_all("/api/ipam/vlans/")
    if as_json:
        click.echo(json.dumps(vlans, indent=2))
        return
    table = Table(box=box.SIMPLE, pad_edge=False, show_edge=False)
    table.add_column("ID",    style="dim",  no_wrap=True, justify="right", width=6)
    table.add_column("VID",   style="bold", no_wrap=True, justify="right", width=6)
    table.add_column("Name",  style="cyan", no_wrap=True)
    table.add_column("Site",  style="dim",  no_wrap=True)
    table.add_column("Group", style="dim",  no_wrap=True)
    table.add_column("Role",  style="dim",  no_wrap=True)
    table.add_column("Status",              no_wrap=True)
    for v in vlans:
        table.add_row(
            str(v["id"]),
            str(v.get("vid", "—")),
            v.get("name") or "—",
            _nested(v.get("site"),  "name"),
            _nested(v.get("group"), "name"),
            _nested(v.get("role"),  "name"),
            _colored_status(_nested(v.get("status"), "value")),
        )
    console.print(table)
    console.print(f"[dim]{len(vlans)} VLAN(s)[/dim]")


# ---------------------------------------------------------------------------
# tenant group
# ---------------------------------------------------------------------------

@cli.group("tenant")
def grp_tenant():
    """Manage tenants (Tenancy)."""


@grp_tenant.command("list")
@click.option("--json", "as_json", is_flag=True)
def tenant_list(as_json):
    """List tenants."""
    tenants = api_get_all("/api/tenancy/tenants/")
    if as_json:
        click.echo(json.dumps(tenants, indent=2))
        return
    table = Table(box=box.SIMPLE, pad_edge=False, show_edge=False)
    table.add_column("ID",    style="dim",  no_wrap=True, justify="right", width=6)
    table.add_column("Name",  style="bold", no_wrap=True)
    table.add_column("Slug",  style="dim",  no_wrap=True)
    table.add_column("Group", style="dim",  no_wrap=True)
    table.add_column("Desc",  style="dim",  no_wrap=True)
    for t in tenants:
        table.add_row(
            str(t["id"]),
            t.get("name") or "—",
            t.get("slug") or "—",
            _nested(t.get("group"), "name"),
            t.get("description") or "—",
        )
    console.print(table)
    console.print(f"[dim]{len(tenants)} tenant(s)[/dim]")


# ---------------------------------------------------------------------------
# contact group
# ---------------------------------------------------------------------------

@cli.group("contact")
def grp_contact():
    """Manage contacts (Tenancy)."""


@grp_contact.command("list")
@click.option("--json", "as_json", is_flag=True)
def contact_list(as_json):
    """List contacts."""
    contacts = api_get_all("/api/tenancy/contacts/")
    if as_json:
        click.echo(json.dumps(contacts, indent=2))
        return
    table = Table(box=box.SIMPLE, pad_edge=False, show_edge=False)
    table.add_column("ID",    style="dim",  no_wrap=True, justify="right", width=6)
    table.add_column("Name",  style="bold", no_wrap=True)
    table.add_column("Title", style="dim",  no_wrap=True)
    table.add_column("Email", style="cyan", no_wrap=True)
    table.add_column("Phone", style="dim",  no_wrap=True)
    for c in contacts:
        table.add_row(
            str(c["id"]),
            c.get("name") or "—",
            c.get("title") or "—",
            c.get("email") or "—",
            c.get("phone") or "—",
        )
    console.print(table)
    console.print(f"[dim]{len(contacts)} contact(s)[/dim]")


# ---------------------------------------------------------------------------
# completion group
# ---------------------------------------------------------------------------

@cli.group("completion")
def grp_completion():
    """Generate shell tab-completion scripts."""


@grp_completion.command("bash")
def completion_bash():
    """Print bash completion setup instructions."""
    console.print("Add this line to your [bold]~/.bashrc[/bold]:")
    console.print('  eval "$(_NETBOX_CLI_COMPLETE=bash_source netbox-cli)"')


@grp_completion.command("zsh")
def completion_zsh():
    """Print zsh completion setup instructions."""
    console.print("Add this line to your [bold]~/.zshrc[/bold]:")
    console.print('  eval "$(_NETBOX_CLI_COMPLETE=zsh_source netbox-cli)"')


@grp_completion.command("fish")
def completion_fish():
    """Print fish completion setup instructions."""
    console.print("Add this line to your [bold]~/.config/fish/config.fish[/bold]:")
    console.print("  eval (env _NETBOX_CLI_COMPLETE=fish_source netbox-cli)")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    cli()
