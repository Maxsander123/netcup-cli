from __future__ import annotations

from urllib.parse import quote

import click

from netcup_cli import __version__
from netcup_cli.auth import AuthClient
from netcup_cli.client import SCPClient, build_client
from netcup_cli.config import Credentials, delete_credentials, load_credentials, save_credentials
from netcup_cli.errors import CLIError
from netcup_cli.output import console, print_result, print_server, print_servers

import shutil
import subprocess as _subprocess
from netcup_cli.safety import confirm_action

# Advanced subgroups
from netcup_cli.commands.disks import disks_group
from netcup_cli.commands.images import server_iso_group, server_snapshots_group
from netcup_cli.commands.metrics import metrics_group
from netcup_cli.commands.misc import api_group, maintenance_group
from netcup_cli.commands.networking import rdns_group, server_interfaces_group, vlans_group
from netcup_cli.commands.tasks import tasks_group
from netcup_cli.commands.users import users_group


def _q(s: str) -> str:
    return quote(str(s), safe="")


def _resolve(client: SCPClient, name: str) -> str:
    """Resolve nickname, hostname, or numeric ID to a server ID string."""
    if str(name).isdigit():
        return str(name)
    servers = client.request("GET", "/servers")
    items: list[dict] = servers if isinstance(servers, list) else (servers or {}).get("data", [])  # type: ignore[union-attr]
    for s in items:
        if s.get("nickname") == name or s.get("hostname") == name or str(s.get("id")) == name:
            return str(s["id"])
    raise CLIError(f"No server found for '{name}'. Use 'netcup-cli list' to see available servers.")


@click.group()
@click.version_option(__version__, prog_name="netcup-cli")
@click.option("--json", "as_json", is_flag=True, default=False, help="Output raw JSON.")
@click.pass_context
def cli(ctx: click.Context, as_json: bool) -> None:
    """netcup-cli — Netcup Server Control Panel CLI."""
    ctx.ensure_object(dict)
    ctx.obj["json"] = as_json


# ── auth ──────────────────────────────────────────────────────────────────────

@cli.command("login")
def cmd_login() -> None:
    """Login via browser (device code — no password needed)."""
    client = AuthClient()
    token_set = client.login_device()
    save_credentials(Credentials(refresh_token=token_set.refresh_token))  # type: ignore[arg-type]
    console.print("[green]✓[/green] Logged in.")


@cli.command("logout")
def cmd_logout() -> None:
    """Remove locally saved credentials."""
    delete_credentials()
    console.print("[green]✓[/green] Logged out.")


@cli.command("whoami")
def cmd_whoami() -> None:
    """Show login status."""
    creds = load_credentials()
    if creds is None:
        console.print("[yellow]Not logged in.[/yellow]  Run: netcup-cli login")
    else:
        console.print("[green]Logged in.[/green]  Refresh token stored locally.")


# ── server list / info ────────────────────────────────────────────────────────

@cli.command("list")
@click.pass_context
def cmd_list(ctx: click.Context) -> None:
    """List all servers."""
    client = build_client()
    result = client.request("GET", "/servers")
    servers: list[dict] = result if isinstance(result, list) else (result or {}).get("data", [])  # type: ignore[union-attr]
    print_servers(servers, as_json=ctx.obj.get("json", False))


@cli.command("info")
@click.argument("server")
@click.pass_context
def cmd_info(ctx: click.Context, server: str) -> None:
    """Show details for a server (ID, nickname, or hostname)."""
    client = build_client()
    server_id = _resolve(client, server)
    result = client.request("GET", f"/servers/{_q(server_id)}")
    print_server(result, as_json=ctx.obj.get("json", False))  # type: ignore[arg-type]


# `get` as alias for `info`
@cli.command("get", hidden=True)
@click.argument("server")
@click.pass_context
def cmd_get(ctx: click.Context, server: str) -> None:
    """Alias for 'info'."""
    ctx.invoke(cmd_info, server=server)


# ── power commands ────────────────────────────────────────────────────────────

@cli.command("start")
@click.argument("server")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.pass_context
def cmd_start(ctx: click.Context, server: str, yes: bool) -> None:
    """Start a server."""
    client = build_client()
    server_id = _resolve(client, server)
    confirm_action(f"Start server {server} ({server_id})?", yes=yes)
    result = client.request("POST", f"/servers/{_q(server_id)}/power", json_body={"action": "START"})
    print_result(result, as_json=ctx.obj.get("json", False))


@cli.command("stop")
@click.argument("server")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.pass_context
def cmd_stop(ctx: click.Context, server: str, yes: bool) -> None:
    """Gracefully stop a server."""
    client = build_client()
    server_id = _resolve(client, server)
    confirm_action(f"Stop server {server} ({server_id})?", yes=yes)
    result = client.request("POST", f"/servers/{_q(server_id)}/power", json_body={"action": "STOP"})
    print_result(result, as_json=ctx.obj.get("json", False))


@cli.command("reset")
@click.argument("server")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.pass_context
def cmd_reset(ctx: click.Context, server: str, yes: bool) -> None:
    """Hard-reset (reboot) a server."""
    client = build_client()
    server_id = _resolve(client, server)
    confirm_action(f"Hard-reset server {server} ({server_id})? This interrupts the server.", yes=yes)
    result = client.request("POST", f"/servers/{_q(server_id)}/power", json_body={"action": "HARD_REBOOT"})
    print_result(result, as_json=ctx.obj.get("json", False))


# ── vnc ───────────────────────────────────────────────────────────────────────

_VNC_BASE = "https://www.servercontrolpanel.de/scp-ui/servers"


def _open_browser(url: str) -> None:
    for opener in ("xdg-open", "sensible-browser", "x-www-browser", "firefox", "chromium-browser", "google-chrome"):
        if shutil.which(opener):
            _subprocess.Popen([opener, url], stdout=_subprocess.DEVNULL, stderr=_subprocess.DEVNULL)
            return
    console.print(f"[yellow]No browser found. Open manually:[/yellow]\n  {url}")


@cli.command("vnc")
@click.argument("server")
@click.option("--url-only", is_flag=True, help="Print the URL instead of opening the browser.")
@click.pass_context
def cmd_vnc(ctx: click.Context, server: str, url_only: bool) -> None:
    """Open the VNC/serial console for a server in the browser."""
    client = build_client()
    server_id = _resolve(client, server)
    url = f"{_VNC_BASE}/{server_id}/screen"
    if url_only:
        click.echo(url)
        return
    console.print(f"Opening VNC console for [bold]{server}[/bold] ({server_id}) ...")
    console.print(f"[dim]{url}[/dim]")
    console.print("[dim]Log in to servercontrolpanel.de in the browser if prompted.[/dim]")
    _open_browser(url)


# ── snapshot subgroup ─────────────────────────────────────────────────────────

@cli.group("snapshot")
def snapshot_group() -> None:
    """Manage server snapshots."""


@snapshot_group.command("list")
@click.argument("server")
@click.pass_context
def snapshot_list(ctx: click.Context, server: str) -> None:
    """List snapshots for a server."""
    client = build_client()
    server_id = _resolve(client, server)
    result = client.request("GET", f"/servers/{_q(server_id)}/snapshots")
    print_result(result, as_json=ctx.obj.get("json", False))


@snapshot_group.command("create")
@click.argument("server")
@click.option("--name", "-n", required=True, help="Snapshot name.")
@click.option("--description", "-d", default="", help="Optional description.")
@click.pass_context
def snapshot_create(ctx: click.Context, server: str, name: str, description: str) -> None:
    """Create a snapshot."""
    client = build_client()
    server_id = _resolve(client, server)
    body: dict = {"name": name}
    if description:
        body["description"] = description
    result = client.request("POST", f"/servers/{_q(server_id)}/snapshots", json_body=body)
    print_result(result, as_json=ctx.obj.get("json", False))


@snapshot_group.command("delete")
@click.argument("server")
@click.argument("snapshot_id")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.pass_context
def snapshot_delete(ctx: click.Context, server: str, snapshot_id: str, yes: bool) -> None:
    """Delete a snapshot. Cannot be undone."""
    client = build_client()
    server_id = _resolve(client, server)
    confirm_action(f"Delete snapshot {snapshot_id} from {server}? Cannot be undone.", yes=yes)
    result = client.request("DELETE", f"/servers/{_q(server_id)}/snapshots/{_q(snapshot_id)}")
    print_result(result, as_json=ctx.obj.get("json", False))


@snapshot_group.command("restore")
@click.argument("server")
@click.argument("snapshot_id")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.pass_context
def snapshot_restore(ctx: click.Context, server: str, snapshot_id: str, yes: bool) -> None:
    """Restore a server from a snapshot. All current disk data will be lost."""
    client = build_client()
    server_id = _resolve(client, server)
    confirm_action(
        f"Restore snapshot {snapshot_id} onto {server}? All current disk data will be lost.",
        yes=yes,
    )
    result = client.request("POST", f"/servers/{_q(server_id)}/snapshots/{_q(snapshot_id)}/revert")
    print_result(result, as_json=ctx.obj.get("json", False))


@snapshot_group.command("export")
@click.argument("server")
@click.argument("snapshot_id")
@click.pass_context
def snapshot_export(ctx: click.Context, server: str, snapshot_id: str) -> None:
    """Export a snapshot."""
    client = build_client()
    server_id = _resolve(client, server)
    result = client.request("POST", f"/servers/{_q(server_id)}/snapshots/{_q(snapshot_id)}/export")
    print_result(result, as_json=ctx.obj.get("json", False))


# ── advanced subgroups ────────────────────────────────────────────────────────

cli.add_command(rdns_group)
cli.add_command(tasks_group)
cli.add_command(users_group)
cli.add_command(vlans_group)
cli.add_command(api_group)
cli.add_command(maintenance_group)

from netcup_cli.commands.servers import servers_group
servers_group.add_command(disks_group)
servers_group.add_command(server_iso_group, name="iso")
servers_group.add_command(server_interfaces_group, name="interfaces")
servers_group.add_command(metrics_group)
servers_group.add_command(server_snapshots_group, name="snapshots")
cli.add_command(servers_group)


@cli.command("completion")
@click.argument("shell", type=click.Choice(["bash", "zsh", "fish"]))
def completion(shell: str) -> None:
    """Print shell completion script."""
    import os
    import subprocess
    result = subprocess.run(
        ["python3", "-m", "netcup_cli"],
        env={**os.environ, "_NETCUP_CLI_COMPLETE": f"{shell}_source"},
        capture_output=True,
        text=True,
    )
    click.echo(result.stdout, nl=False)
