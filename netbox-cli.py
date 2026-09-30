#!/usr/bin/env python3
"""netbox-cli — Manage NetBox DCIM/IPAM/Virtualization from the terminal."""
from __future__ import annotations

import json
import os
import sys
import time
import webbrowser
from concurrent.futures import ThreadPoolExecutor, as_completed
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
@click.argument("address", metavar="ADDRESS")
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


# ===========================================================================
# Netcup — embedded client + commands
# ===========================================================================

_NC_CREDS_FILE  = CONFIG_DIR / "netcup.json"
_NC_AUTH_BASE   = "https://www.servercontrolpanel.de/realms/scp/protocol/openid-connect"
_NC_DEVICE_EP   = f"{_NC_AUTH_BASE}/auth/device"
_NC_TOKEN_EP    = f"{_NC_AUTH_BASE}/token"
_NC_CLIENT_ID   = "scp"
_NC_API_BASE    = "https://www.servercontrolpanel.de/scp-core/api/v1"

_NC_STATE_MAP: dict[str, str] = {
    "RUNNING": "running", "STOPPED": "stopped", "SHUTOFF": "stopped",
    "PAUSED": "stopped", "BUILDING": "deploying",
}


def _nc_save_creds(data: dict) -> None:
    CONFIG_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
    tmp = _NC_CREDS_FILE.with_suffix(".tmp")
    fd = os.open(str(tmp), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        os.write(fd, json.dumps(data, indent=2).encode())
    finally:
        os.close(fd)
    tmp.replace(_NC_CREDS_FILE)


def _nc_load_creds() -> dict:
    if not _NC_CREDS_FILE.exists():
        console.print("[red]Netcup not logged in.[/red] Run: netbox-cli netcup login")
        sys.exit(1)
    try:
        return json.loads(_NC_CREDS_FILE.read_text())
    except (json.JSONDecodeError, OSError) as exc:
        console.print(f"[red]Netcup config error:[/red] {exc}")
        sys.exit(1)


def _nc_access_token() -> str:
    """Return a valid access token, refreshing silently if needed."""
    creds = _nc_load_creds()
    if creds.get("access_token") and creds.get("access_token_expires_at", 0) > time.time() + 30:
        return creds["access_token"]
    resp = requests.post(
        _NC_TOKEN_EP,
        data={
            "client_id":    _NC_CLIENT_ID,
            "grant_type":   "refresh_token",
            "refresh_token": creds["refresh_token"],
        },
        timeout=15,
    )
    if not resp.ok:
        try:
            msg = resp.json().get("error_description", str(resp.status_code))
        except Exception:
            msg = str(resp.status_code)
        console.print(f"[red]Netcup token refresh failed:[/red] {msg}")
        console.print("Run: [bold]netbox-cli netcup login[/bold]")
        sys.exit(1)
    tok = resp.json()
    creds["access_token"] = tok["access_token"]
    creds["access_token_expires_at"] = time.time() + tok.get("expires_in", 300)
    if "refresh_token" in tok:
        creds["refresh_token"] = tok["refresh_token"]
    _nc_save_creds(creds)
    return tok["access_token"]


def _nc_hdrs(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Accept": "application/json"}


def _nc_primary_ipv4(detail: dict) -> str:
    addrs = detail.get("ipv4Addresses") or []
    return addrs[0]["ip"] if addrs else "—"


def _nc_public_ipv6(detail: dict) -> str | None:
    live   = detail.get("serverLiveInfo") or {}
    ifaces = live.get("interfaces") or []
    primary = next((i for i in ifaces if not i.get("vlanInterface")), None)
    if not primary:
        return None
    prefixes = primary.get("ipv6NetworkPrefixes") or []
    mac = primary.get("mac")
    if not prefixes or not mac:
        return None
    prefix = prefixes[0].split("/")[0].rstrip(":")
    parts  = mac.split(":")
    parts.insert(3, "ff")
    parts.insert(4, "fe")
    parts[0] = format(int(parts[0], 16) ^ 0x02, "02x")
    eui64   = "".join(parts[i] + parts[i + 1] for i in range(0, 8, 2))
    groups  = ":".join(eui64[i:i + 4] for i in range(0, 16, 4))
    return f"{prefix}:{groups}"


def _nc_state(detail: dict) -> str:
    raw = (detail.get("serverLiveInfo") or {}).get("state", "")
    return _NC_STATE_MAP.get(raw.upper(), raw.lower() or "—")


def _nc_location(detail: dict) -> str:
    return (detail.get("site") or {}).get("city", "—") or "—"


def _nc_vlan_names(token: str) -> dict[int, str]:
    try:
        r = requests.get(f"{_NC_API_BASE}/cloudvlans", headers=_nc_hdrs(token), timeout=10)
        if r.ok:
            items = r.json()
            if isinstance(items, list):
                return {v["id"]: v.get("name") or str(v["id"]) for v in items if v.get("id")}
    except Exception:
        pass
    return {}


def _nc_get_detail(server_id, token: str) -> dict:
    r = requests.get(f"{_NC_API_BASE}/servers/{server_id}", headers=_nc_hdrs(token), timeout=15)
    r.raise_for_status()
    return r.json()


def _nc_fetch_servers() -> list[dict]:
    """Return list of server dicts each with a 'detail' key added."""
    token   = _nc_access_token()
    r = requests.get(f"{_NC_API_BASE}/servers", headers=_nc_hdrs(token), timeout=15)
    r.raise_for_status()
    data    = r.json()
    servers = data if isinstance(data, list) else data.get("data", [])
    vlan_names = _nc_vlan_names(token)

    details: dict = {}
    with ThreadPoolExecutor(max_workers=min(len(servers) or 1, 8)) as pool:
        future_map = {pool.submit(_nc_get_detail, s["id"], token): s["id"] for s in servers}
        for fut in as_completed(future_map):
            sid = future_map[fut]
            try:
                details[sid] = fut.result()
            except Exception:
                details[sid] = {}

    out = []
    for s in servers:
        sid    = s.get("id")
        detail = details.get(sid, {})
        live   = detail.get("serverLiveInfo") or {}
        ifaces = live.get("interfaces") or []
        primary_iface = next((i for i in ifaces if not i.get("vlanInterface")), {})
        disks  = live.get("disks") or []
        disk_mib = sum(d.get("capacityInMiB", 0) for d in disks)
        ipv6_prefixes = primary_iface.get("ipv6NetworkPrefixes") or []

        eth_idx  = 0
        networks = []
        for iface in ifaces:
            mac = iface.get("mac")
            if not mac:
                continue
            vlan_id = iface.get("vlanId")
            if iface.get("vlanInterface") and vlan_id:
                label = vlan_names.get(vlan_id) or f"vlan{vlan_id}"
            else:
                label = f"eth{eth_idx}"
                eth_idx += 1
            networks.append({
                "port": label, "mac": mac,
                "ip": next(
                    (a.get("ip") for a in (iface.get("ipAddresses") or [])
                     if a.get("type") == "public" and "." in (a.get("ip") or "")),
                    None,
                ),
            })

        vlan_ifaces = [i for i in ifaces if i.get("vlanInterface")]
        vlans = [
            {
                "nic": vi.get("mac") or "",
                "mac": vi.get("mac") or "",
                "vlan": vlan_names.get(vi.get("vlanId")) if vi.get("vlanId") else vi.get("vlanId"),
            }
            for vi in vlan_ifaces
        ]

        hostname = s.get("hostname", "—")
        nickname = s.get("nickname") or ""
        out.append({
            "id":       str(sid),
            "name":     nickname if nickname and nickname != hostname else hostname,
            "hostname": hostname,
            "nickname": nickname or None,
            "status":   _nc_state(detail),
            "ip":       _nc_primary_ipv4(detail),
            "location": _nc_location(detail),
            "template": (s.get("template") or {}).get("name"),
            "arch":     detail.get("architecture"),
            "mac":      primary_iface.get("mac"),
            "networks": networks or None,
            "ipv6":     _nc_public_ipv6(detail),
            "ipv6_prefix": ipv6_prefixes[0] if ipv6_prefixes else None,
            "vcpus":    live.get("cpuCount"),
            "memory_mb": live.get("currentServerMemoryInMiB"),
            "disk_gb":  round(disk_mib / 1024) if disk_mib else None,
            "rx_month_gb": round(primary_iface.get("rxMonthlyInMiB", 0) / 1024, 1),
            "tx_month_gb": round(primary_iface.get("txMonthlyInMiB", 0) / 1024, 1),
            "vlans":    vlans or None,
            "_detail":  detail,
        })
    return out


def _nc_resolve(name: str) -> dict:
    servers = _nc_fetch_servers()
    matches = [
        s for s in servers
        if s["id"] == name or s["name"] == name or s.get("hostname") == name
    ]
    if not matches:
        console.print(f"[red]Netcup server not found:[/red] {name}")
        sys.exit(1)
    return matches[0]


def _nc_find_server_id(name: str) -> str:
    token   = _nc_access_token()
    r = requests.get(f"{_NC_API_BASE}/servers", headers=_nc_hdrs(token), timeout=15)
    r.raise_for_status()
    data    = r.json()
    servers = data if isinstance(data, list) else data.get("data", [])
    matches = [
        s for s in servers
        if str(s.get("id")) == name or s.get("hostname") == name or (s.get("nickname") or "") == name
    ]
    if not matches:
        console.print(f"[red]Netcup server not found:[/red] {name}")
        sys.exit(1)
    if len(matches) > 1:
        lines = "\n".join(f"  {s['id']}  {s.get('nickname') or s.get('hostname')}" for s in matches)
        console.print(f"[red]Ambiguous name '{name}':[/red]\n{lines}")
        sys.exit(1)
    return str(matches[0]["id"])


def _nc_power_action(server: dict, action: str) -> None:
    token = _nc_access_token()
    r = requests.post(
        f"{_NC_API_BASE}/servers/{server['id']}/{action}",
        headers={**_nc_hdrs(token), "Content-Type": "application/json"},
        json={},
        timeout=30,
    )
    if not r.ok:
        console.print(f"[red]Netcup API {r.status_code}:[/red] {r.text[:200]}")
        sys.exit(1)


# ── netcup command group ──────────────────────────────────────────────────────

@cli.group("netcup")
def grp_netcup():
    """Manage Netcup VPS servers."""


@grp_netcup.command("login")
def netcup_login():
    """Login to Netcup SCP via browser (OAuth2 Device Code flow — persistent)."""
    resp = requests.post(
        _NC_DEVICE_EP,
        data={"client_id": _NC_CLIENT_ID, "scope": "offline_access"},
        timeout=15,
    )
    if not resp.ok:
        console.print(f"[red]Login failed:[/red] {resp.text}")
        sys.exit(1)
    data        = resp.json()
    uri         = data.get("verification_uri_complete") or data.get("verification_uri")
    device_code = data["device_code"]
    interval    = data.get("interval", 5)

    console.print(f"\n[bold yellow]Öffne diese URL im Browser:[/bold yellow]\n  {uri}\n")
    if "verification_uri_complete" not in data:
        console.print(f"  Code: [bold]{data.get('user_code')}[/bold]\n")

    webbrowser.open(uri)

    sys.stdout.write("Warte auf Browser-Authentifizierung")
    sys.stdout.flush()
    while True:
        time.sleep(interval)
        r = requests.post(
            _NC_TOKEN_EP,
            data={
                "client_id":   _NC_CLIENT_ID,
                "grant_type":  "urn:ietf:params:oauth:grant-type:device_code",
                "device_code": device_code,
            },
            timeout=15,
        )
        tok = r.json()
        if r.ok:
            sys.stdout.write("\n")
            sys.stdout.flush()
            _nc_save_creds({"refresh_token": tok["refresh_token"]})
            console.print("[green]✓[/green] Erfolgreich eingeloggt. Credentials persistent gespeichert.")
            return
        err = tok.get("error", "")
        if err == "authorization_pending":
            sys.stdout.write(".")
            sys.stdout.flush()
        elif err == "slow_down":
            interval += 5
        else:
            sys.stdout.write("\n")
            console.print(f"[red]Auth-Fehler:[/red] {tok}")
            sys.exit(1)


@grp_netcup.command("logout")
def netcup_logout():
    """Remove saved Netcup credentials."""
    if _NC_CREDS_FILE.exists():
        _NC_CREDS_FILE.unlink()
        console.print("[green]✓[/green] Netcup logged out.")
    else:
        console.print("Netcup not logged in.")


@grp_netcup.command("list")
@click.option("--format", "-f", "fmt", type=click.Choice(["table", "json", "csv"]), default="table", show_default=True)
def netcup_list(fmt: str):
    """List Netcup VPS servers."""
    servers = _nc_fetch_servers()

    if fmt == "json":
        click.echo(json.dumps([{k: v for k, v in s.items() if k != "_detail"} for s in servers], indent=2))
        return

    if fmt == "csv":
        click.echo("id,name,hostname,status,ip,location")
        for s in servers:
            click.echo(f"{s['id']},{s['name']},{s.get('hostname','—')},{s['status']},{s['ip']},{s['location']}")
        return

    table = Table(box=box.ROUNDED)
    table.add_column("ID");      table.add_column("Name", style="bold")
    table.add_column("Hostname"); table.add_column("Status"); table.add_column("IP"); table.add_column("Location")
    for s in servers:
        table.add_row(s["id"], s["name"], s.get("hostname") or "—", s["status"], s["ip"], s["location"])
    console.print(table)
    console.print(f"[dim]{len(servers)} server(s)[/dim]")


@grp_netcup.command("info")
@click.argument("name")
@click.option("--raw", is_flag=True, help="Dump raw API JSON.")
def netcup_info(name: str, raw: bool):
    """Show details for a Netcup VPS."""
    if raw:
        token     = _nc_access_token()
        server_id = _nc_find_server_id(name)
        detail    = _nc_get_detail(server_id, token)
        click.echo(json.dumps(detail, indent=2))
        return
    s     = _nc_resolve(name)
    t, rw = _detail_table()
    rw("ID",          s["id"])
    rw("Name",        s["name"])
    rw("Hostname",    s.get("hostname"))
    rw("Status",      s["status"])
    rw("IP",          s["ip"])
    rw("Location",    s["location"])
    rw("IPv6",        s.get("ipv6") or "—")
    rw("Template",    s.get("template") or "—")
    rw("Arch",        s.get("arch") or "—")
    rw("vCPUs",       s.get("vcpus"))
    mem = s.get("memory_mb")
    rw("RAM",         f"{mem // 1024}G ({mem} MB)" if mem else "—")
    rw("Disk",        f"{s.get('disk_gb')}G" if s.get("disk_gb") else "—")
    rw("MAC",         s.get("mac") or "—")
    rw("RX/month",    f"{s.get('rx_month_gb', 0)} GB")
    rw("TX/month",    f"{s.get('tx_month_gb', 0)} GB")
    console.print(t)


@grp_netcup.command("start")
@click.argument("name")
@click.option("--force", "-f", is_flag=True, help="Skip confirmation.")
def netcup_start(name: str, force: bool):
    """Start a Netcup VPS."""
    s = _nc_resolve(name)
    if not force:
        click.confirm(f"Start '{s['name']}' ({s['status']}, {s['ip']})?", abort=True)
    _nc_power_action(s, "start")
    console.print(f"[green]✓[/green] {s['name']} start gesendet.")


@grp_netcup.command("stop")
@click.argument("name")
@click.option("--force", "-f", is_flag=True, help="Skip confirmation.")
def netcup_stop(name: str, force: bool):
    """Stop a Netcup VPS."""
    s = _nc_resolve(name)
    if not force:
        click.confirm(f"Stop '{s['name']}' ({s['status']}, {s['ip']})?", abort=True)
    _nc_power_action(s, "stop")
    console.print(f"[green]✓[/green] {s['name']} stop gesendet.")


@grp_netcup.command("reset")
@click.argument("name")
@click.option("--force", "-f", is_flag=True, help="Skip confirmation.")
def netcup_reset(name: str, force: bool):
    """Hard-reset (reboot) a Netcup VPS."""
    s = _nc_resolve(name)
    if not force:
        click.confirm(f"Hard-reset '{s['name']}' ({s['status']}, {s['ip']})?", abort=True)
    _nc_power_action(s, "reboot")
    console.print(f"[green]✓[/green] {s['name']} reset gesendet.")


@grp_netcup.command("traffic")
@click.argument("name", required=False, default=None)
@click.option("--format", "-f", "fmt", type=click.Choice(["table", "json", "csv"]), default="table", show_default=True)
def netcup_traffic(name: str | None, fmt: str):
    """Show monthly traffic usage. Without NAME shows all servers."""
    servers = _nc_fetch_servers()
    if name:
        servers = [s for s in servers if s["id"] == name or s["name"] == name or s.get("hostname") == name]
        if not servers:
            console.print(f"[red]Server not found:[/red] {name}")
            sys.exit(1)

    rows = [
        {"name": s["name"], "rx_gb": s.get("rx_month_gb", 0),
         "tx_gb": s.get("tx_month_gb", 0),
         "total_gb": round((s.get("rx_month_gb") or 0) + (s.get("tx_month_gb") or 0), 1)}
        for s in servers
    ]

    if fmt == "json":
        click.echo(json.dumps(rows, indent=2))
        return
    if fmt == "csv":
        click.echo("name,rx_gb,tx_gb,total_gb")
        for row in rows:
            click.echo(f"{row['name']},{row['rx_gb']},{row['tx_gb']},{row['total_gb']}")
        return

    table = Table(box=box.ROUNDED, title="Monthly Traffic")
    table.add_column("Name", style="bold")
    table.add_column("RX GB",    justify="right")
    table.add_column("TX GB",    justify="right")
    table.add_column("Total GB", justify="right", style="bold cyan")
    for row in rows:
        table.add_row(row["name"], str(row["rx_gb"]), str(row["tx_gb"]), str(row["total_gb"]))
    console.print(table)


# ── netcup snapshot subgroup ──────────────────────────────────────────────────

@grp_netcup.group("snapshot")
def netcup_snapshot():
    """Manage Netcup VPS snapshots."""


@netcup_snapshot.command("list")
@click.argument("name")
def nc_snapshot_list(name: str):
    """List snapshots for a Netcup server."""
    token     = _nc_access_token()
    server_id = _nc_find_server_id(name)
    r = requests.get(f"{_NC_API_BASE}/servers/{server_id}/snapshots", headers=_nc_hdrs(token), timeout=15)
    if not r.ok:
        console.print(f"[red]Netcup API {r.status_code}:[/red] {r.text[:200]}")
        sys.exit(1)
    data  = r.json()
    snaps = data if isinstance(data, list) else data.get("data", [])
    if not snaps:
        console.print("No snapshots found.")
        return
    table = Table(title=f"Snapshots — {name}", box=box.ROUNDED)
    table.add_column("ID",      style="bold cyan", no_wrap=True)
    table.add_column("Name",    style="bold")
    table.add_column("Created", style="dim")
    table.add_column("Size",    justify="right")
    for s in snaps:
        raw_size = s.get("sizeInMiB") or s.get("size")
        table.add_row(
            str(s.get("id", "—")),
            s.get("name") or "—",
            s.get("createdAt") or s.get("created") or "—",
            f"{raw_size} MiB" if raw_size is not None else "—",
        )
    console.print(table)


@netcup_snapshot.command("create")
@click.argument("name")
@click.option("--snap-name", default=None, help="Name for the new snapshot (prompted if omitted).")
@click.option("--description", "-d", default="", help="Optional description.")
def nc_snapshot_create(name: str, snap_name: str | None, description: str):
    """Create a snapshot for a Netcup server."""
    token     = _nc_access_token()
    server_id = _nc_find_server_id(name)
    if not snap_name:
        snap_name = click.prompt("Snapshot name")
    body: dict = {"name": snap_name}
    if description:
        body["description"] = description
    r = requests.post(
        f"{_NC_API_BASE}/servers/{server_id}/snapshots",
        headers={**_nc_hdrs(token), "Content-Type": "application/json"},
        json=body,
        timeout=60,
    )
    if not r.ok:
        console.print(f"[red]Netcup API {r.status_code}:[/red] {r.text[:200]}")
        sys.exit(1)
    result  = r.json() if r.content else {}
    snap_id = result.get("id", "?")
    console.print(f"[green]✓[/green] Snapshot '{snap_name}' erstellt (id={snap_id}).")


@netcup_snapshot.command("delete")
@click.argument("name")
@click.argument("snap_id")
@click.option("--force", "-f", is_flag=True, help="Skip confirmation.")
def nc_snapshot_delete(name: str, snap_id: str, force: bool):
    """Delete a snapshot from a Netcup server."""
    token     = _nc_access_token()
    server_id = _nc_find_server_id(name)
    if not force:
        click.confirm(f"Snapshot {snap_id} von '{name}' löschen? Kann nicht rückgängig gemacht werden.", abort=True)
    r = requests.delete(
        f"{_NC_API_BASE}/servers/{server_id}/snapshots/{snap_id}",
        headers=_nc_hdrs(token),
        timeout=30,
    )
    if not r.ok:
        console.print(f"[red]Netcup API {r.status_code}:[/red] {r.text[:200]}")
        sys.exit(1)
    console.print(f"[green]✓[/green] Snapshot {snap_id} gelöscht.")


@netcup_snapshot.command("restore")
@click.argument("name")
@click.argument("snap_id")
@click.option("--force", "-f", is_flag=True, help="Skip confirmation.")
def nc_snapshot_restore(name: str, snap_id: str, force: bool):
    """Restore a Netcup server from a snapshot.

    WARNING: Overwrites the current disk — all data since the snapshot is lost.
    """
    token     = _nc_access_token()
    server_id = _nc_find_server_id(name)
    console.print(
        "\n[bold red]WARNUNG:[/bold red] Restore überschreibt die aktuelle Disk.\n"
        "Alle Daten nach dem Snapshot-Zeitpunkt gehen verloren.\n"
    )
    if not force:
        click.confirm(f"Snapshot {snap_id} auf '{name}' wiederherstellen?", abort=True)
    r = requests.post(
        f"{_NC_API_BASE}/servers/{server_id}/snapshots/{snap_id}/restore",
        headers={**_nc_hdrs(token), "Content-Type": "application/json"},
        json={},
        timeout=60,
    )
    if not r.ok:
        console.print(f"[red]Netcup API {r.status_code}:[/red] {r.text[:200]}")
        sys.exit(1)
    console.print(f"[green]✓[/green] Snapshot {snap_id} auf '{name}' wiederhergestellt.")


# ── netcup register / sync / deregister ───────────────────────────────────────

_JANUS_FIELDS = [("vendor", "Vendor"), ("janus_id", "Janus ID"), ("cpu_type", "CPU Type")]


def _nc_nb_ensure_custom_fields() -> None:
    """Create janus tracking custom fields in NetBox if missing (best-effort)."""
    cfg   = load_config()
    base  = cfg["url"]
    hdrs  = _headers()
    names = ",".join(n for n, _ in _JANUS_FIELDS)
    try:
        existing = api_get("/api/extras/custom-fields/", params={"name__in": names, "limit": 20})
        existing_names = {cf["name"] for cf in existing.get("results", [])}
        for field_name, label in _JANUS_FIELDS:
            if field_name not in existing_names:
                requests.post(
                    base + "/api/extras/custom-fields/",
                    headers=hdrs,
                    json={
                        "name":         field_name,
                        "label":        label,
                        "type":         "text",
                        "object_types": ["dcim.device", "virtualization.virtualmachine"],
                        "required":     False,
                    },
                    verify=False,
                    timeout=20,
                )
    except Exception:
        pass


def _nc_nb_tag(endpoint: str, service: str, resource_id: str, arch: str | None) -> None:
    """Write vendor/janus_id/cpu_type custom fields. Creates fields if missing."""
    cf: dict = {"vendor": service, "janus_id": resource_id}
    if arch:
        cf["cpu_type"] = arch
    r = requests.patch(
        load_config()["url"] + endpoint,
        headers=_headers(),
        json={"custom_fields": cf},
        verify=False,
        timeout=20,
    )
    if r.ok:
        return
    if r.status_code == 400 and "does not exist" in r.text:
        _nc_nb_ensure_custom_fields()
        requests.patch(
            load_config()["url"] + endpoint,
            headers=_headers(),
            json={"custom_fields": cf},
            verify=False,
            timeout=20,
        )


def _nc_nb_get_or_create_cluster() -> int:
    clusters = api_get_all("/api/virtualization/clusters/")
    if clusters:
        if len(clusters) == 1:
            console.print(f"  Cluster: {clusters[0]['name']} (auto-gewählt)")
            return clusters[0]["id"]
        console.print("\nVerfügbare Cluster:")
        for i, c in enumerate(clusters, 1):
            console.print(f"  {i:2}. {c['name']}")
        while True:
            raw = click.prompt("Cluster").strip()
            if raw.isdigit():
                idx = int(raw) - 1
                if 0 <= idx < len(clusters):
                    return clusters[idx]["id"]
            for c in clusters:
                if c["name"].lower() == raw.lower():
                    return c["id"]
            console.print(f"  Bitte 1–{len(clusters)} oder exakter Name.")
    console.print("\nKein Cluster gefunden — erstelle einen.")
    cname = click.prompt("Cluster-Name", default="Default")
    ctypes = api_get_all("/api/virtualization/cluster-types/")
    if ctypes:
        ctype_id = ctypes[0]["id"]
    else:
        ct_name = click.prompt("Cluster-Typ", default="Generic")
        ct = api_post("/api/virtualization/cluster-types/",
                      {"name": ct_name, "slug": ct_name.lower().replace(" ", "-")})
        ctype_id = ct["id"]
    cluster = api_post("/api/virtualization/clusters/", {"name": cname, "type": ctype_id})
    console.print(f"  Cluster '{cname}' erstellt (id={cluster['id']})")
    return cluster["id"]


@grp_netcup.command("register")
@click.argument("name")
@click.option("--yes", "-y", is_flag=True, help="Skip all confirmations.")
def netcup_register(name: str, yes: bool):
    """Register a Netcup VPS in NetBox as a virtual machine.

    Creates the VM, interfaces, IP addresses, and tracking custom fields.
    Prompts interactively for cluster if more than one exists.
    """
    load_config()  # ensure netbox is configured
    s = _nc_resolve(name)

    # Check if already registered
    existing = api_get_all("/api/virtualization/virtual-machines/", {"name": s["name"]})
    if existing:
        console.print(f"[yellow]VM '{s['name']}' already exists in NetBox (id={existing[0]['id']}).[/yellow]")
        if not yes and not click.confirm("Update tracking fields and continue?"):
            return
        vm_id = existing[0]["id"]
    else:
        cluster_id = _nc_nb_get_or_create_cluster()
        _nc_nb_ensure_custom_fields()

        body: dict = {
            "name":    s["name"],
            "cluster": cluster_id,
            "status":  "active" if s["status"] == "running" else "offline",
        }
        if s.get("vcpus"):    body["vcpus"]  = s["vcpus"]
        if s.get("memory_mb"): body["memory"] = s["memory_mb"]
        if s.get("disk_gb"):  body["disk"]   = s["disk_gb"]

        vm = api_post("/api/virtualization/virtual-machines/", body)
        vm_id = vm["id"]
        console.print(f"[green]✓[/green] VM '{s['name']}' in NetBox erstellt (id={vm_id}).")

    # Tag tracking fields
    _nc_nb_tag(f"/api/virtualization/virtual-machines/{vm_id}/", "netcup", s["id"], s.get("arch"))

    # Create interfaces
    networks = s.get("networks") or []
    primary_iface_id = None
    for iface in networks:
        mac   = (iface.get("mac") or "").upper()
        pname = iface.get("port") or "eth0"
        if not mac:
            continue
        existing_ifaces = api_get_all("/api/virtualization/interfaces/",
                                      {"virtual_machine_id": vm_id, "name": pname})
        if existing_ifaces:
            iface_id = existing_ifaces[0]["id"]
        else:
            iface_obj = api_post("/api/virtualization/interfaces/",
                                 {"virtual_machine": vm_id, "name": pname, "mac_address": mac})
            iface_id = iface_obj["id"]
            console.print(f"  Interface {pname} ({mac}) erstellt.")
        if primary_iface_id is None:
            primary_iface_id = iface_id

        # Assign IP if available
        iface_ip = iface.get("ip")
        if iface_ip and primary_iface_id == iface_id:
            addr = f"{iface_ip}/32"
            existing_ips = api_get_all("/api/ipam/ip-addresses/", {"address": iface_ip})
            if existing_ips:
                ip_id = existing_ips[0]["id"]
            else:
                ip_obj = api_post("/api/ipam/ip-addresses/", {
                    "address": addr, "status": "active",
                    "assigned_object_type": "virtualization.vminterface",
                    "assigned_object_id":   iface_id,
                })
                ip_id = ip_obj["id"]
                console.print(f"  IP {addr} erstellt.")
            api_patch(f"/api/virtualization/virtual-machines/{vm_id}/", {"primary_ip4": ip_id})
            console.print(f"  Primary IP gesetzt: {addr}")

    console.print(f"[green]✓[/green] '{s['name']}' in NetBox registriert.")


@grp_netcup.command("sync")
@click.option("--dry-run", is_flag=True, help="Show changes without applying them.")
@click.option("--sync-ip", is_flag=True, help="Also reconcile primary IP.")
@click.option("--sync-interfaces", is_flag=True, help="Also reconcile interfaces.")
def netcup_sync(dry_run: bool, sync_ip: bool, sync_interfaces: bool):
    """Sync live Netcup VPS state to NetBox (status, IP, interfaces).

    Only updates VMs that were registered via 'netcup register' and have
    the janus_id tracking field set.
    """
    load_config()
    _STATUS_MAP = {
        "running": "active", "stopped": "offline", "deploying": "staged",
    }

    console.print("[dim]Fetching Netcup servers…[/dim]")
    servers = _nc_fetch_servers()
    by_id   = {s["id"]: s for s in servers}

    console.print("[dim]Loading NetBox VMs…[/dim]")
    vms = api_get_all("/api/virtualization/virtual-machines/")
    nb_by_janus_id = {
        (vm.get("custom_fields") or {}).get("janus_id"): vm
        for vm in vms
        if (vm.get("custom_fields") or {}).get("vendor") == "netcup"
           and (vm.get("custom_fields") or {}).get("janus_id")
    }

    if not nb_by_janus_id:
        console.print("[yellow]Keine via 'netcup register' erfassten VMs gefunden.[/yellow]")
        console.print("Führe zuerst: netbox-cli netcup register <name>")
        return

    changed = 0
    for janus_id, nb_vm in nb_by_janus_id.items():
        live = by_id.get(janus_id)
        if not live:
            console.print(f"  [yellow]{nb_vm.get('name')}[/yellow]: nicht mehr bei Netcup vorhanden.")
            continue

        updates: dict = {}
        nb_status = (nb_vm.get("status") or {}).get("value", "")
        new_status = _STATUS_MAP.get(live["status"], "")
        if new_status and nb_status != new_status:
            updates["status"] = new_status

        vm_name = live["name"]
        if nb_vm.get("name") != vm_name:
            updates["name"] = vm_name

        if updates:
            changed += 1
            if dry_run:
                console.print(f"  [cyan]{nb_vm.get('name')}[/cyan]: würde aktualisieren → {updates}")
            else:
                api_patch(f"/api/virtualization/virtual-machines/{nb_vm['id']}/", updates)
                console.print(f"  [green]✓[/green] {vm_name}: {updates}")

        if sync_ip and live.get("ip") and live["ip"] != "—":
            raw = ((nb_vm.get("primary_ip4") or {}).get("address") or "").split("/")[0]
            if raw != live["ip"]:
                if dry_run:
                    console.print(f"  [cyan]{vm_name}[/cyan]: IP {raw or '—'} → {live['ip']}")
                else:
                    addr = f"{live['ip']}/32"
                    existing = api_get_all("/api/ipam/ip-addresses/", {"address": live["ip"]})
                    if existing:
                        ip_id = existing[0]["id"]
                    else:
                        ifaces = api_get_all("/api/virtualization/interfaces/",
                                             {"virtual_machine_id": nb_vm["id"], "limit": 1})
                        if ifaces:
                            ip_obj = api_post("/api/ipam/ip-addresses/", {
                                "address": addr, "status": "active",
                                "assigned_object_type": "virtualization.vminterface",
                                "assigned_object_id":   ifaces[0]["id"],
                            })
                            ip_id = ip_obj["id"]
                        else:
                            continue
                    api_patch(f"/api/virtualization/virtual-machines/{nb_vm['id']}/", {"primary_ip4": ip_id})
                    console.print(f"  [green]✓[/green] {vm_name}: IP → {live['ip']}")
                changed += 1

        if sync_interfaces and live.get("networks"):
            for iface in live["networks"]:
                mac   = (iface.get("mac") or "").upper()
                pname = iface.get("port") or "eth0"
                if not mac:
                    continue
                existing = api_get_all("/api/virtualization/interfaces/",
                                       {"virtual_machine_id": nb_vm["id"], "name": pname})
                if existing:
                    nb_mac = (existing[0].get("mac_address") or "").upper()
                    if nb_mac != mac:
                        if dry_run:
                            console.print(f"  [cyan]{vm_name}[/cyan]: {pname} MAC {nb_mac or '—'} → {mac}")
                        else:
                            api_patch(f"/api/virtualization/interfaces/{existing[0]['id']}/",
                                      {"mac_address": mac})
                            console.print(f"  [green]✓[/green] {vm_name}: {pname} MAC → {mac}")
                        changed += 1
                else:
                    if dry_run:
                        console.print(f"  [cyan]{vm_name}[/cyan]: {pname} ({mac}) erstellen")
                    else:
                        api_post("/api/virtualization/interfaces/",
                                 {"virtual_machine": nb_vm["id"], "name": pname, "mac_address": mac})
                        console.print(f"  [green]✓[/green] {vm_name}: Interface {pname} erstellt.")
                    changed += 1

    prefix = "[dim](dry-run)[/dim] " if dry_run else ""
    console.print(f"\n{prefix}Sync abgeschlossen. {changed} Änderung(en).")


@grp_netcup.command("deregister")
@click.argument("name")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
def netcup_deregister(name: str, yes: bool):
    """Remove a Netcup VPS from NetBox (deletes the VM record)."""
    load_config()
    vms = api_get_all("/api/virtualization/virtual-machines/", {"name": name})
    if not vms:
        console.print(f"[red]VM '{name}' not found in NetBox.[/red]")
        sys.exit(1)
    vm = vms[0]
    if not yes:
        if not Confirm.ask(f"Delete VM [bold]{vm.get('name')}[/bold] (id={vm['id']}) from NetBox?"):
            console.print("Aborted.")
            return
    api_delete(f"/api/virtualization/virtual-machines/{vm['id']}/")
    console.print(f"[green]✓[/green] '{name}' aus NetBox entfernt.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    cli()
