from __future__ import annotations

from urllib.parse import quote

import click

from netcup_cli import __version__
from netcup_cli.auth import AuthClient
from netcup_cli.client import build_client
from netcup_cli.config import Credentials, delete_credentials, load_credentials, save_credentials
from netcup_cli.errors import CLIError
from netcup_cli.output import console, print_result
from netcup_cli.safety import confirm_action

# Advanced subgroups (still accessible for power users)
from netcup_cli.commands.disks import disks_group
from netcup_cli.commands.images import server_iso_group, server_snapshots_group
from netcup_cli.commands.metrics import metrics_group
from netcup_cli.commands.misc import api_group, maintenance_group
from netcup_cli.commands.networking import rdns_group, server_interfaces_group, vlans_group
from netcup_cli.commands.tasks import tasks_group
from netcup_cli.commands.users import users_group


def _q(s: str) -> str:
    return quote(str(s), safe="")


@click.group()
@click.version_option(__version__, prog_name="netcup-cli")
@click.option("--json", "as_json", is_flag=True, default=False, help="Output raw JSON.")
@click.pass_context
def cli(ctx: click.Context, as_json: bool) -> None:
    """netcup-cli — Netcup Server Control Panel CLI."""
    ctx.ensure_object(dict)
    ctx.obj["json"] = as_json


# ── auth (flat) ───────────────────────────────────────────────────────────────

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
        console.print("[green]Logged in.[/green]  A refresh token is stored locally.")


# ── server shortcuts (flat) ───────────────────────────────────────────────────

@cli.command("list")
@click.pass_context
def cmd_list(ctx: click.Context) -> None:
    """List all servers."""
    client = build_client()
    result = client.request("GET", "/servers")
    print_result(result, as_json=ctx.obj.get("json", False))


@cli.command("info")
@click.argument("server_id")
@click.pass_context
def cmd_info(ctx: click.Context, server_id: str) -> None:
    """Show details for a server."""
    client = build_client()
    result = client.request("GET", f"/servers/{_q(server_id)}")
    print_result(result, as_json=ctx.obj.get("json", False))


@cli.command("start")
@click.argument("server_id")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.pass_context
def cmd_start(ctx: click.Context, server_id: str, yes: bool) -> None:
    """Start a server."""
    confirm_action(f"Start server {server_id}?", yes=yes)
    client = build_client()
    result = client.request("POST", f"/servers/{_q(server_id)}/power", json_body={"action": "START"})
    print_result(result, as_json=ctx.obj.get("json", False))


@cli.command("stop")
@click.argument("server_id")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.pass_context
def cmd_stop(ctx: click.Context, server_id: str, yes: bool) -> None:
    """Gracefully stop a server."""
    confirm_action(f"Stop server {server_id}?", yes=yes)
    client = build_client()
    result = client.request("POST", f"/servers/{_q(server_id)}/power", json_body={"action": "STOP"})
    print_result(result, as_json=ctx.obj.get("json", False))


@cli.command("reset")
@click.argument("server_id")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.pass_context
def cmd_reset(ctx: click.Context, server_id: str, yes: bool) -> None:
    """Hard-reset (reboot) a server."""
    confirm_action(f"Hard-reset server {server_id}? This interrupts the server.", yes=yes)
    client = build_client()
    result = client.request("POST", f"/servers/{_q(server_id)}/power", json_body={"action": "HARD_REBOOT"})
    print_result(result, as_json=ctx.obj.get("json", False))


# ── snapshot subgroup (flat, common) ─────────────────────────────────────────

@cli.group("snapshot")
def snapshot_group() -> None:
    """Manage server snapshots."""


@snapshot_group.command("list")
@click.argument("server_id")
@click.pass_context
def snapshot_list(ctx: click.Context, server_id: str) -> None:
    """List snapshots for a server."""
    client = build_client()
    result = client.request("GET", f"/servers/{_q(server_id)}/snapshots")
    print_result(result, as_json=ctx.obj.get("json", False))


@snapshot_group.command("create")
@click.argument("server_id")
@click.option("--name", "-n", required=True, help="Snapshot name.")
@click.option("--description", "-d", default="", help="Optional description.")
@click.pass_context
def snapshot_create(ctx: click.Context, server_id: str, name: str, description: str) -> None:
    """Create a snapshot."""
    client = build_client()
    body: dict = {"name": name}
    if description:
        body["description"] = description
    result = client.request("POST", f"/servers/{_q(server_id)}/snapshots", json_body=body)
    print_result(result, as_json=ctx.obj.get("json", False))


@snapshot_group.command("delete")
@click.argument("server_id")
@click.argument("snapshot_id")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.pass_context
def snapshot_delete(ctx: click.Context, server_id: str, snapshot_id: str, yes: bool) -> None:
    """Delete a snapshot. Cannot be undone."""
    confirm_action(f"Delete snapshot {snapshot_id} from server {server_id}? This cannot be undone.", yes=yes)
    client = build_client()
    result = client.request("DELETE", f"/servers/{_q(server_id)}/snapshots/{_q(snapshot_id)}")
    print_result(result, as_json=ctx.obj.get("json", False))


@snapshot_group.command("restore")
@click.argument("server_id")
@click.argument("snapshot_id")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.pass_context
def snapshot_restore(ctx: click.Context, server_id: str, snapshot_id: str, yes: bool) -> None:
    """Restore a server from a snapshot. All current disk data will be lost."""
    confirm_action(
        f"Restore snapshot {snapshot_id} onto server {server_id}? "
        "All current disk data will be lost.",
        yes=yes,
    )
    client = build_client()
    result = client.request("POST", f"/servers/{_q(server_id)}/snapshots/{_q(snapshot_id)}/revert")
    print_result(result, as_json=ctx.obj.get("json", False))


@snapshot_group.command("export")
@click.argument("server_id")
@click.argument("snapshot_id")
@click.pass_context
def snapshot_export(ctx: click.Context, server_id: str, snapshot_id: str) -> None:
    """Export a snapshot."""
    client = build_client()
    result = client.request("POST", f"/servers/{_q(server_id)}/snapshots/{_q(snapshot_id)}/export")
    print_result(result, as_json=ctx.obj.get("json", False))


# ── advanced subgroups ────────────────────────────────────────────────────────

cli.add_command(rdns_group)
cli.add_command(tasks_group)
cli.add_command(users_group)
cli.add_command(vlans_group)
cli.add_command(api_group)
cli.add_command(maintenance_group)

# servers group — advanced operations (disks, interfaces, metrics, etc.)
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
