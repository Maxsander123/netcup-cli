#!/usr/bin/env python3
"""netbox-cli — Standalone Netcup VPS management CLI."""
from __future__ import annotations

import json
import os
import sys
import time
import webbrowser
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import click
import requests
from rich import box
from rich.console import Console
from rich.table import Table

VERSION    = "3.0.0"
CONFIG_DIR = Path.home() / ".config" / "netbox-cli"
CREDS_FILE = CONFIG_DIR / "netcup.json"
AUTH_BASE  = "https://www.servercontrolpanel.de/realms/scp/protocol/openid-connect"
DEVICE_EP  = f"{AUTH_BASE}/auth/device"
TOKEN_EP   = f"{AUTH_BASE}/token"
CLIENT_ID  = "scp"
API_BASE   = "https://www.servercontrolpanel.de/scp-core/api/v1"

STATE_MAP: dict[str, str] = {
    "RUNNING": "running", "STOPPED": "stopped", "SHUTOFF": "stopped",
    "PAUSED": "stopped", "BUILDING": "deploying",
}

console = Console()


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

def _save_creds(data: dict) -> None:
    CONFIG_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
    tmp = CREDS_FILE.with_suffix(".tmp")
    fd = os.open(str(tmp), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        os.write(fd, json.dumps(data, indent=2).encode())
    finally:
        os.close(fd)
    tmp.replace(CREDS_FILE)


def _load_creds() -> dict:
    if not CREDS_FILE.exists():
        console.print("[red]Nicht eingeloggt.[/red] Führe aus: netbox-cli login")
        sys.exit(1)
    try:
        return json.loads(CREDS_FILE.read_text())
    except (json.JSONDecodeError, OSError) as exc:
        console.print(f"[red]Konfigurationsfehler:[/red] {exc}")
        sys.exit(1)


def access_token() -> str:
    """Return a valid access token, refreshing silently when needed."""
    creds = _load_creds()
    if creds.get("access_token") and creds.get("expires_at", 0) > time.time() + 30:
        return creds["access_token"]
    resp = requests.post(
        TOKEN_EP,
        data={
            "client_id":     CLIENT_ID,
            "grant_type":    "refresh_token",
            "refresh_token": creds["refresh_token"],
        },
        timeout=15,
    )
    if not resp.ok:
        try:
            msg = resp.json().get("error_description", str(resp.status_code))
        except Exception:
            msg = str(resp.status_code)
        console.print(f"[red]Token-Refresh fehlgeschlagen:[/red] {msg}")
        console.print("Erneut einloggen: [bold]netbox-cli login[/bold]")
        sys.exit(1)
    tok = resp.json()
    creds["access_token"] = tok["access_token"]
    creds["expires_at"]   = time.time() + tok.get("expires_in", 300)
    if "refresh_token" in tok:
        creds["refresh_token"] = tok["refresh_token"]
    _save_creds(creds)
    return tok["access_token"]


def hdrs(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Accept": "application/json"}


# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------

def _primary_ipv4(detail: dict) -> str:
    addrs = detail.get("ipv4Addresses") or []
    return addrs[0]["ip"] if addrs else "—"


def _public_ipv6(detail: dict) -> str | None:
    live    = detail.get("serverLiveInfo") or {}
    ifaces  = live.get("interfaces") or []
    primary = next((i for i in ifaces if not i.get("vlanInterface")), None)
    if not primary:
        return None
    prefixes = primary.get("ipv6NetworkPrefixes") or []
    mac = primary.get("mac")
    if not prefixes or not mac:
        return None
    prefix = prefixes[0].split("/")[0].rstrip(":")
    parts  = mac.split(":")
    parts.insert(3, "ff"); parts.insert(4, "fe")
    parts[0] = format(int(parts[0], 16) ^ 0x02, "02x")
    eui64  = "".join(parts[i] + parts[i + 1] for i in range(0, 8, 2))
    groups = ":".join(eui64[i:i + 4] for i in range(0, 16, 4))
    return f"{prefix}:{groups}"


def _state(detail: dict) -> str:
    raw = (detail.get("serverLiveInfo") or {}).get("state", "")
    return STATE_MAP.get(raw.upper(), raw.lower() or "—")


def _location(detail: dict) -> str:
    return (detail.get("site") or {}).get("city", "—") or "—"


def _vlan_names(token: str) -> dict[int, str]:
    try:
        r = requests.get(f"{API_BASE}/cloudvlans", headers=hdrs(token), timeout=10)
        if r.ok:
            items = r.json()
            if isinstance(items, list):
                return {v["id"]: v.get("name") or str(v["id"]) for v in items if v.get("id")}
    except Exception:
        pass
    return {}


def _get_detail(server_id, token: str) -> dict:
    r = requests.get(f"{API_BASE}/servers/{server_id}", headers=hdrs(token), timeout=15)
    r.raise_for_status()
    return r.json()


def fetch_servers() -> list[dict]:
    token      = access_token()
    r = requests.get(f"{API_BASE}/servers", headers=hdrs(token), timeout=15)
    r.raise_for_status()
    data       = r.json()
    servers    = data if isinstance(data, list) else data.get("data", [])
    vlan_names = _vlan_names(token)

    details: dict = {}
    with ThreadPoolExecutor(max_workers=min(len(servers) or 1, 8)) as pool:
        future_map = {pool.submit(_get_detail, s["id"], token): s["id"] for s in servers}
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
        disks    = live.get("disks") or []
        disk_mib = sum(d.get("capacityInMiB", 0) for d in disks)
        ipv6_pref = (primary_iface.get("ipv6NetworkPrefixes") or [None])[0]

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
                label = f"eth{eth_idx}"; eth_idx += 1
            networks.append({
                "port": label, "mac": mac,
                "ip": next(
                    (a.get("ip") for a in (iface.get("ipAddresses") or [])
                     if a.get("type") == "public" and "." in (a.get("ip") or "")),
                    None,
                ),
            })

        hostname = s.get("hostname", "—")
        nickname = s.get("nickname") or ""
        out.append({
            "id":          str(sid),
            "name":        nickname if nickname and nickname != hostname else hostname,
            "hostname":    hostname,
            "nickname":    nickname or None,
            "status":      _state(detail),
            "ip":          _primary_ipv4(detail),
            "location":    _location(detail),
            "template":    (s.get("template") or {}).get("name"),
            "arch":        detail.get("architecture"),
            "mac":         primary_iface.get("mac"),
            "networks":    networks or None,
            "ipv6":        _public_ipv6(detail),
            "ipv6_prefix": ipv6_pref,
            "vcpus":       live.get("cpuCount"),
            "memory_mb":   live.get("currentServerMemoryInMiB"),
            "disk_gb":     round(disk_mib / 1024) if disk_mib else None,
            "rx_month_gb": round(primary_iface.get("rxMonthlyInMiB", 0) / 1024, 1),
            "tx_month_gb": round(primary_iface.get("txMonthlyInMiB", 0) / 1024, 1),
        })
    return out


def resolve_server(name: str) -> dict:
    servers = fetch_servers()
    matches = [s for s in servers if s["id"] == name or s["name"] == name or s.get("hostname") == name]
    if not matches:
        console.print(f"[red]Server nicht gefunden:[/red] {name}")
        sys.exit(1)
    return matches[0]


def find_server_id(name: str) -> str:
    token   = access_token()
    r = requests.get(f"{API_BASE}/servers", headers=hdrs(token), timeout=15)
    r.raise_for_status()
    data    = r.json()
    servers = data if isinstance(data, list) else data.get("data", [])
    matches = [
        s for s in servers
        if str(s.get("id")) == name or s.get("hostname") == name or (s.get("nickname") or "") == name
    ]
    if not matches:
        console.print(f"[red]Server nicht gefunden:[/red] {name}")
        sys.exit(1)
    if len(matches) > 1:
        lines = "\n".join(f"  {s['id']}  {s.get('nickname') or s.get('hostname')}" for s in matches)
        console.print(f"[red]Mehrdeutiger Name '{name}':[/red]\n{lines}")
        sys.exit(1)
    return str(matches[0]["id"])


def power_action(server: dict, action: str) -> None:
    token = access_token()
    r = requests.post(
        f"{API_BASE}/servers/{server['id']}/{action}",
        headers={**hdrs(token), "Content-Type": "application/json"},
        json={},
        timeout=30,
    )
    if not r.ok:
        console.print(f"[red]API {r.status_code}:[/red] {r.text[:200]}")
        sys.exit(1)


def _detail_table() -> tuple[Table, callable]:
    table = Table(box=box.SIMPLE, show_header=False, pad_edge=False)
    table.add_column("Key",   style="dim",  width=18)
    table.add_column("Value", style="bold")
    def row(k, v):
        table.add_row(k, str(v) if v is not None else "—")
    return table, row


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

@click.group()
@click.version_option(VERSION, prog_name="netbox-cli")
def cli():
    """netbox-cli — Netcup VPS verwalten."""


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

@cli.command("login")
def cmd_login():
    """Login via Browser (OAuth2 Device Code — persistent)."""
    resp = requests.post(
        DEVICE_EP,
        data={"client_id": CLIENT_ID, "scope": "offline_access"},
        timeout=15,
    )
    if not resp.ok:
        console.print(f"[red]Login fehlgeschlagen:[/red] {resp.text}")
        sys.exit(1)
    data        = resp.json()
    uri         = data.get("verification_uri_complete") or data.get("verification_uri")
    device_code = data["device_code"]
    interval    = data.get("interval", 5)

    console.print(f"\n[bold yellow]URL im Browser öffnen:[/bold yellow]\n  {uri}\n")
    if "verification_uri_complete" not in data:
        console.print(f"  Code: [bold]{data.get('user_code')}[/bold]\n")

    webbrowser.open(uri)
    sys.stdout.write("Warte auf Browser-Authentifizierung")
    sys.stdout.flush()

    while True:
        time.sleep(interval)
        r = requests.post(
            TOKEN_EP,
            data={
                "client_id":   CLIENT_ID,
                "grant_type":  "urn:ietf:params:oauth:grant-type:device_code",
                "device_code": device_code,
            },
            timeout=15,
        )
        tok = r.json()
        if r.ok:
            sys.stdout.write("\n")
            sys.stdout.flush()
            _save_creds({"refresh_token": tok["refresh_token"]})
            console.print("[green]✓[/green] Eingeloggt. Credentials persistent gespeichert.")
            return
        err = tok.get("error", "")
        if err == "authorization_pending":
            sys.stdout.write("."); sys.stdout.flush()
        elif err == "slow_down":
            interval += 5
        else:
            sys.stdout.write("\n")
            console.print(f"[red]Fehler:[/red] {tok}")
            sys.exit(1)


@cli.command("logout")
def cmd_logout():
    """Gespeicherte Credentials entfernen."""
    if CREDS_FILE.exists():
        CREDS_FILE.unlink()
        console.print("[green]✓[/green] Ausgeloggt.")
    else:
        console.print("Nicht eingeloggt.")


# ---------------------------------------------------------------------------
# Server
# ---------------------------------------------------------------------------

@cli.command("list")
@click.option("--format", "-f", "fmt", type=click.Choice(["table", "json", "csv"]), default="table", show_default=True)
def cmd_list(fmt: str):
    """Alle VPS-Server auflisten."""
    servers = fetch_servers()

    if fmt == "json":
        click.echo(json.dumps(servers, indent=2))
        return
    if fmt == "csv":
        click.echo("id,name,hostname,status,ip,location")
        for s in servers:
            click.echo(f"{s['id']},{s['name']},{s.get('hostname','—')},{s['status']},{s['ip']},{s['location']}")
        return

    table = Table(box=box.ROUNDED)
    table.add_column("ID")
    table.add_column("Name",     style="bold")
    table.add_column("Hostname")
    table.add_column("Status")
    table.add_column("IP")
    table.add_column("Location")
    for s in servers:
        table.add_row(s["id"], s["name"], s.get("hostname") or "—", s["status"], s["ip"], s["location"])
    console.print(table)
    console.print(f"[dim]{len(servers)} server[/dim]")


@cli.command("info")
@click.argument("name")
@click.option("--raw", is_flag=True, help="Rohe API-JSON-Ausgabe.")
def cmd_info(name: str, raw: bool):
    """Details zu einem Server anzeigen."""
    if raw:
        detail = _get_detail(find_server_id(name), access_token())
        click.echo(json.dumps(detail, indent=2))
        return
    s     = resolve_server(name)
    t, rw = _detail_table()
    rw("ID",        s["id"])
    rw("Name",      s["name"])
    rw("Hostname",  s.get("hostname"))
    rw("Status",    s["status"])
    rw("IP",        s["ip"])
    rw("Location",  s["location"])
    rw("IPv6",      s.get("ipv6") or "—")
    rw("Template",  s.get("template") or "—")
    rw("Arch",      s.get("arch") or "—")
    rw("vCPUs",     s.get("vcpus"))
    mem = s.get("memory_mb")
    rw("RAM",       f"{mem // 1024}G ({mem} MB)" if mem else "—")
    rw("Disk",      f"{s.get('disk_gb')}G" if s.get("disk_gb") else "—")
    rw("MAC",       s.get("mac") or "—")
    rw("RX/Monat",  f"{s.get('rx_month_gb', 0)} GB")
    rw("TX/Monat",  f"{s.get('tx_month_gb', 0)} GB")
    console.print(t)


# ---------------------------------------------------------------------------
# Power
# ---------------------------------------------------------------------------

@cli.command("start")
@click.argument("name")
@click.option("--force", "-f", is_flag=True, help="Ohne Bestätigung.")
def cmd_start(name: str, force: bool):
    """Server starten."""
    s = resolve_server(name)
    if not force:
        click.confirm(f"'{s['name']}' starten ({s['status']}, {s['ip']})?", abort=True)
    power_action(s, "start")
    console.print(f"[green]✓[/green] {s['name']} gestartet.")


@cli.command("stop")
@click.argument("name")
@click.option("--force", "-f", is_flag=True, help="Ohne Bestätigung.")
def cmd_stop(name: str, force: bool):
    """Server stoppen."""
    s = resolve_server(name)
    if not force:
        click.confirm(f"'{s['name']}' stoppen ({s['status']}, {s['ip']})?", abort=True)
    power_action(s, "stop")
    console.print(f"[green]✓[/green] {s['name']} gestoppt.")


@cli.command("reset")
@click.argument("name")
@click.option("--force", "-f", is_flag=True, help="Ohne Bestätigung.")
def cmd_reset(name: str, force: bool):
    """Server hard-resetten (Reboot)."""
    s = resolve_server(name)
    if not force:
        click.confirm(f"'{s['name']}' hard-resetten ({s['status']}, {s['ip']})?", abort=True)
    power_action(s, "reboot")
    console.print(f"[green]✓[/green] {s['name']} zurückgesetzt.")


# ---------------------------------------------------------------------------
# Traffic
# ---------------------------------------------------------------------------

@cli.command("traffic")
@click.argument("name", required=False, default=None)
@click.option("--format", "-f", "fmt", type=click.Choice(["table", "json", "csv"]), default="table", show_default=True)
def cmd_traffic(name: str | None, fmt: str):
    """Monatlichen Traffic anzeigen. Ohne NAME alle Server."""
    servers = fetch_servers()
    if name:
        servers = [s for s in servers if s["id"] == name or s["name"] == name or s.get("hostname") == name]
        if not servers:
            console.print(f"[red]Server nicht gefunden:[/red] {name}")
            sys.exit(1)

    rows = [
        {
            "name":     s["name"],
            "rx_gb":    s.get("rx_month_gb", 0),
            "tx_gb":    s.get("tx_month_gb", 0),
            "total_gb": round((s.get("rx_month_gb") or 0) + (s.get("tx_month_gb") or 0), 1),
        }
        for s in servers
    ]

    if fmt == "json":
        click.echo(json.dumps(rows, indent=2)); return
    if fmt == "csv":
        click.echo("name,rx_gb,tx_gb,total_gb")
        for row in rows:
            click.echo(f"{row['name']},{row['rx_gb']},{row['tx_gb']},{row['total_gb']}")
        return

    table = Table(box=box.ROUNDED, title="Monatlicher Traffic")
    table.add_column("Name",     style="bold")
    table.add_column("RX GB",    justify="right")
    table.add_column("TX GB",    justify="right")
    table.add_column("Total GB", justify="right", style="bold cyan")
    for row in rows:
        table.add_row(row["name"], str(row["rx_gb"]), str(row["tx_gb"]), str(row["total_gb"]))
    console.print(table)


# ---------------------------------------------------------------------------
# Snapshots
# ---------------------------------------------------------------------------

@cli.group("snapshot")
def grp_snapshot():
    """Snapshots verwalten."""


@grp_snapshot.command("list")
@click.argument("name")
def snapshot_list(name: str):
    """Snapshots eines Servers auflisten."""
    token     = access_token()
    server_id = find_server_id(name)
    r = requests.get(f"{API_BASE}/servers/{server_id}/snapshots", headers=hdrs(token), timeout=15)
    if not r.ok:
        console.print(f"[red]API {r.status_code}:[/red] {r.text[:200]}")
        sys.exit(1)
    data  = r.json()
    snaps = data if isinstance(data, list) else data.get("data", [])
    if not snaps:
        console.print("Keine Snapshots gefunden.")
        return
    table = Table(title=f"Snapshots — {name}", box=box.ROUNDED)
    table.add_column("ID",       style="bold cyan", no_wrap=True)
    table.add_column("Name",     style="bold")
    table.add_column("Erstellt", style="dim")
    table.add_column("Größe",    justify="right")
    for s in snaps:
        raw_size = s.get("sizeInMiB") or s.get("size")
        table.add_row(
            str(s.get("id", "—")),
            s.get("name") or "—",
            s.get("createdAt") or s.get("created") or "—",
            f"{raw_size} MiB" if raw_size is not None else "—",
        )
    console.print(table)


@grp_snapshot.command("create")
@click.argument("name")
@click.option("--snap-name", default=None, help="Name des Snapshots (wird abgefragt wenn nicht angegeben).")
@click.option("--description", "-d", default="", help="Optionale Beschreibung.")
def snapshot_create(name: str, snap_name: str | None, description: str):
    """Snapshot eines Servers erstellen."""
    token     = access_token()
    server_id = find_server_id(name)
    if not snap_name:
        snap_name = click.prompt("Snapshot-Name")
    body: dict = {"name": snap_name}
    if description:
        body["description"] = description
    r = requests.post(
        f"{API_BASE}/servers/{server_id}/snapshots",
        headers={**hdrs(token), "Content-Type": "application/json"},
        json=body,
        timeout=60,
    )
    if not r.ok:
        console.print(f"[red]API {r.status_code}:[/red] {r.text[:200]}")
        sys.exit(1)
    result  = r.json() if r.content else {}
    snap_id = result.get("id", "?")
    console.print(f"[green]✓[/green] Snapshot '{snap_name}' erstellt (id={snap_id}).")


@grp_snapshot.command("delete")
@click.argument("name")
@click.argument("snap_id")
@click.option("--force", "-f", is_flag=True, help="Ohne Bestätigung.")
def snapshot_delete(name: str, snap_id: str, force: bool):
    """Snapshot eines Servers löschen."""
    token     = access_token()
    server_id = find_server_id(name)
    if not force:
        click.confirm(
            f"Snapshot {snap_id} von '{name}' löschen? Kann nicht rückgängig gemacht werden.",
            abort=True,
        )
    r = requests.delete(
        f"{API_BASE}/servers/{server_id}/snapshots/{snap_id}",
        headers=hdrs(token),
        timeout=30,
    )
    if not r.ok:
        console.print(f"[red]API {r.status_code}:[/red] {r.text[:200]}")
        sys.exit(1)
    console.print(f"[green]✓[/green] Snapshot {snap_id} gelöscht.")


@grp_snapshot.command("restore")
@click.argument("name")
@click.argument("snap_id")
@click.option("--force", "-f", is_flag=True, help="Ohne Bestätigung.")
def snapshot_restore(name: str, snap_id: str, force: bool):
    """Server aus Snapshot wiederherstellen.

    WARNUNG: Überschreibt die aktuelle Disk — alle Daten nach dem Snapshot gehen verloren.
    """
    token     = access_token()
    server_id = find_server_id(name)
    console.print(
        "\n[bold red]WARNUNG:[/bold red] Restore überschreibt die aktuelle Disk.\n"
        "Alle Daten nach dem Snapshot-Zeitpunkt gehen verloren.\n"
    )
    if not force:
        click.confirm(f"Snapshot {snap_id} auf '{name}' wiederherstellen?", abort=True)
    r = requests.post(
        f"{API_BASE}/servers/{server_id}/snapshots/{snap_id}/restore",
        headers={**hdrs(token), "Content-Type": "application/json"},
        json={},
        timeout=60,
    )
    if not r.ok:
        console.print(f"[red]API {r.status_code}:[/red] {r.text[:200]}")
        sys.exit(1)
    console.print(f"[green]✓[/green] Snapshot {snap_id} auf '{name}' wiederhergestellt.")


# ---------------------------------------------------------------------------
# Shell completion
# ---------------------------------------------------------------------------

@cli.group("completion")
def grp_completion():
    """Shell-Completion einrichten."""


@grp_completion.command("bash")
def completion_bash():
    console.print("Zu [bold]~/.bashrc[/bold] hinzufügen:")
    console.print('  eval "$(_NETBOX_CLI_COMPLETE=bash_source netbox-cli)"')


@grp_completion.command("zsh")
def completion_zsh():
    console.print("Zu [bold]~/.zshrc[/bold] hinzufügen:")
    console.print('  eval "$(_NETBOX_CLI_COMPLETE=zsh_source netbox-cli)"')


@grp_completion.command("fish")
def completion_fish():
    console.print("Zu [bold]~/.config/fish/config.fish[/bold] hinzufügen:")
    console.print("  eval (env _NETBOX_CLI_COMPLETE=fish_source netbox-cli)")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    cli()
