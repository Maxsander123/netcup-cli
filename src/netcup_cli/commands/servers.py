from __future__ import annotations

from urllib.parse import quote

import click

from netcup_cli.client import build_client, resolve_server
from netcup_cli.errors import CLIError
from netcup_cli.output import print_result
from netcup_cli.safety import confirm_action


def _q(s: str) -> str:
    return quote(str(s), safe="")


@click.command("set")
@click.argument("server")
@click.option("--nickname", default=None)
@click.option("--hostname", default=None)
@click.option("--autostart/--no-autostart", default=None)
@click.option("--uefi/--no-uefi", default=None)
@click.option("--bootorder", default=None, help="Comma-separated: HDD,CDROM,NETWORK")
@click.option("--keyboard-layout", default=None, help="e.g. de, en-us")
@click.option("--os-optimization", type=click.Choice(["LINUX", "WINDOWS", "BSD", "LINUX_LEGACY", "UNKNOWN"]), default=None)
@click.option("--root-password", is_flag=True, default=False, help="Prompt for and set a new root password.")
@click.option("--yes", "-y", is_flag=True)
@click.pass_context
def servers_set(
    ctx: click.Context,
    server: str,
    nickname: str | None,
    hostname: str | None,
    autostart: bool | None,
    uefi: bool | None,
    bootorder: str | None,
    keyboard_layout: str | None,
    os_optimization: str | None,
    root_password: bool,
    yes: bool,
) -> None:
    """Change server settings (nickname, hostname, boot order, ...). Each option is sent as a separate PATCH (API accepts one at a time)."""
    patches: list[dict] = []
    if nickname is not None:
        patches.append({"nickname": nickname})
    if hostname is not None:
        patches.append({"hostname": hostname})
    if autostart is not None:
        patches.append({"autostart": autostart})
    if uefi is not None:
        patches.append({"uefi": uefi})
    if bootorder:
        patches.append({"bootorder": [b.strip().upper() for b in bootorder.split(",") if b.strip()]})
    if keyboard_layout:
        patches.append({"keyboardLayout": keyboard_layout})
    if os_optimization:
        patches.append({"os_optimization": os_optimization})
    if root_password:
        pw = click.prompt("New root password", hide_input=True, confirmation_prompt=True)
        patches.append({"rootPassword": pw})
    if not patches:
        raise CLIError("Nothing to update. See 'netcup-cli servers update --help'.")
    client = build_client()
    server_id = resolve_server(client, server)
    if uefi is not None or bootorder or root_password:
        confirm_action(f"Apply settings to server {server} ({server_id})?", yes=yes)
    for body in patches:
        result = client.request("PATCH", f"/servers/{_q(server_id)}", json_body=body, merge_patch=True)
        print_result(result, as_json=ctx.obj.get("json", False))


_POWER = {
    "on": ("ON", None),
    "off": ("OFF", None),
    "poweroff": ("OFF", "POWEROFF"),
    "reset": ("ON", "RESET"),
    "powercycle": ("ON", "POWERCYCLE"),
    "suspend": ("SUSPENDED", None),
}


@click.command("power")
@click.argument("server")
@click.argument("action", type=click.Choice(list(_POWER), case_sensitive=False))
@click.option("--yes", "-y", is_flag=True)
@click.pass_context
def servers_power(ctx: click.Context, server: str, action: str, yes: bool) -> None:
    """Change power state: on, off (ACPI), poweroff (hard), reset, powercycle, suspend."""
    client = build_client()
    server_id = resolve_server(client, server)
    confirm_action(f"Apply power action '{action}' to server {server} ({server_id})?", yes=yes)
    state, option = _POWER[action.lower()]
    result = client.request(
        "PATCH",
        f"/servers/{_q(server_id)}",
        params={"stateOption": option} if option else None,
        json_body={"state": state},
        merge_patch=True,
    )
    print_result(result, as_json=ctx.obj.get("json", False))


@click.command("gpu-driver")
@click.argument("server")
@click.pass_context
def servers_gpu_driver(ctx: click.Context, server: str) -> None:
    """Get GPU driver download info for a server."""
    client = build_client()
    result = client.request("GET", f"/servers/{_q(resolve_server(client, server))}/gpu-driver")
    print_result(result, as_json=ctx.obj.get("json", False))


@click.group("guest-agent")
def servers_guest_agent() -> None:
    """QEMU guest agent information."""


@servers_guest_agent.command("get")
@click.argument("server")
@click.pass_context
def guest_agent_get(ctx: click.Context, server: str) -> None:
    """Get guest agent data."""
    client = build_client()
    result = client.request("GET", f"/servers/{_q(resolve_server(client, server))}/guest-agent")
    print_result(result, as_json=ctx.obj.get("json", False))


@servers_guest_agent.command("status")
@click.argument("server")
@click.pass_context
def guest_agent_status(ctx: click.Context, server: str) -> None:
    """Get guest agent status."""
    client = build_client()
    result = client.request("GET", f"/servers/{_q(resolve_server(client, server))}/guest-agent/status")
    print_result(result, as_json=ctx.obj.get("json", False))


@click.command("logs")
@click.argument("server")
@click.option("--limit", type=int, default=20, show_default=True)
@click.option("--offset", type=int, default=0, show_default=True)
@click.pass_context
def servers_logs(ctx: click.Context, server: str, limit: int, offset: int) -> None:
    """List server logs."""
    client = build_client()
    result = client.request(
        "GET", f"/servers/{_q(resolve_server(client, server))}/logs", params={"limit": limit, "offset": offset}
    )
    print_result(result, as_json=ctx.obj.get("json", False))


@click.group("rescue")
def servers_rescue() -> None:
    """Manage the rescue system."""


@servers_rescue.command("status")
@click.argument("server")
@click.pass_context
def rescue_status(ctx: click.Context, server: str) -> None:
    """Show rescue system status."""
    client = build_client()
    result = client.request("GET", f"/servers/{_q(resolve_server(client, server))}/rescuesystem")
    print_result(result, as_json=ctx.obj.get("json", False))


@servers_rescue.command("activate")
@click.argument("server")
@click.option("--yes", "-y", is_flag=True)
@click.pass_context
def rescue_activate(ctx: click.Context, server: str, yes: bool) -> None:
    """Activate the rescue system (reboots the server)."""
    client = build_client()
    server_id = resolve_server(client, server)
    confirm_action(f"Activate rescue system on {server} ({server_id})? The server will reboot.", yes=yes)
    result = client.request("POST", f"/servers/{_q(server_id)}/rescuesystem")
    print_result(result, as_json=ctx.obj.get("json", False))


@servers_rescue.command("deactivate")
@click.argument("server")
@click.option("--yes", "-y", is_flag=True)
@click.pass_context
def rescue_deactivate(ctx: click.Context, server: str, yes: bool) -> None:
    """Deactivate the rescue system."""
    client = build_client()
    server_id = resolve_server(client, server)
    confirm_action(f"Deactivate rescue system on {server} ({server_id})?", yes=yes)
    result = client.request("DELETE", f"/servers/{_q(server_id)}/rescuesystem")
    print_result(result, as_json=ctx.obj.get("json", False))


@click.command("optimize-storage")
@click.argument("server")
@click.option("--disk", "disks", multiple=True, help="Disk name to optimize (repeatable, default: all).")
@click.option("--start/--no-start", default=True, show_default=True, help="Start server after optimization.")
@click.option("--yes", "-y", is_flag=True)
@click.pass_context
def storage_optimize(ctx: click.Context, server: str, disks: tuple[str, ...], start: bool, yes: bool) -> None:
    """Run storage optimization (server must be off)."""
    client = build_client()
    server_id = resolve_server(client, server)
    confirm_action(f"Run storage optimization on {server} ({server_id})?", yes=yes)
    params: dict = {"startAfterOptimization": str(start).lower()}
    if disks:
        params["disks"] = list(disks)
    result = client.request("POST", f"/servers/{_q(server_id)}/storageoptimization", params=params)
    print_result(result, as_json=ctx.obj.get("json", False))
