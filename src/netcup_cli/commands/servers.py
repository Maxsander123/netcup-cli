from __future__ import annotations

import json
from urllib.parse import quote

import click

from netcup_cli.client import build_client
from netcup_cli.output import print_result
from netcup_cli.safety import confirm_action


def _q(s: str) -> str:
    return quote(str(s), safe="")


@click.group("servers")
def servers_group() -> None:
    """Manage SCP servers."""


@servers_group.command("list")
@click.option("--page", type=int, default=None)
@click.option("--page-size", type=int, default=None)
@click.pass_context
def servers_list(ctx: click.Context, page: int | None, page_size: int | None) -> None:
    """List all servers."""
    client = build_client()
    params = {}
    if page is not None:
        params["page"] = page
    if page_size is not None:
        params["pageSize"] = page_size
    result = client.request("GET", "/servers", params=params or None)
    print_result(result, as_json=ctx.obj.get("json", False))


@servers_group.command("get")
@click.argument("server_id")
@click.pass_context
def servers_get(ctx: click.Context, server_id: str) -> None:
    """Get details of a server."""
    client = build_client()
    result = client.request("GET", f"/servers/{_q(server_id)}")
    print_result(result, as_json=ctx.obj.get("json", False))


@servers_group.command("update")
@click.argument("server_id")
@click.option("--nickname", default=None)
@click.option("--state-option", default=None, help="State change (e.g. START, STOP, REBOOT).")
@click.option("--body-file", type=click.Path(exists=True), default=None, help="JSON file with request body.")
@click.option("--yes", "-y", is_flag=True)
@click.pass_context
def servers_update(ctx: click.Context, server_id: str, nickname: str | None, state_option: str | None, body_file: str | None, yes: bool) -> None:
    """Update a server's attributes."""
    if state_option and state_option.upper() in ("STOP", "REBOOT", "HARD_STOP", "HARD_REBOOT"):
        confirm_action(
            f"Apply state '{state_option}' to server {server_id}? This may interrupt the server.",
            yes=yes,
        )
    body: dict = {}
    if body_file:
        body = json.loads(open(body_file).read())
    if nickname is not None:
        body["nickname"] = nickname
    if state_option is not None:
        body["stateOption"] = state_option
    client = build_client()
    result = client.request("PATCH", f"/servers/{_q(server_id)}", json_body=body)
    print_result(result, as_json=ctx.obj.get("json", False))


@servers_group.command("power")
@click.argument("server_id")
@click.argument("action", type=click.Choice(["start", "stop", "reboot", "hard-stop", "hard-reboot"], case_sensitive=False))
@click.option("--yes", "-y", is_flag=True)
@click.pass_context
def servers_power(ctx: click.Context, server_id: str, action: str, yes: bool) -> None:
    """Change the power state of a server."""
    confirm_action(
        f"Apply power action '{action}' to server {server_id}?",
        yes=yes,
        non_interactive_error="Power actions require --yes for non-interactive use.",
    )
    client = build_client()
    result = client.request("POST", f"/servers/{_q(server_id)}/power", json_body={"action": action.upper().replace("-", "_")})
    print_result(result, as_json=ctx.obj.get("json", False))


@servers_group.command("gpu-driver")
@click.argument("server_id")
@click.pass_context
def servers_gpu_driver(ctx: click.Context, server_id: str) -> None:
    """Get GPU driver information for a server."""
    client = build_client()
    result = client.request("GET", f"/servers/{_q(server_id)}/gpu-driver")
    print_result(result, as_json=ctx.obj.get("json", False))


@servers_group.group("guest-agent")
def servers_guest_agent() -> None:
    """Manage guest agent on a server."""


@servers_guest_agent.command("get")
@click.argument("server_id")
@click.pass_context
def guest_agent_get(ctx: click.Context, server_id: str) -> None:
    """Get guest agent configuration."""
    client = build_client()
    result = client.request("GET", f"/servers/{_q(server_id)}/guest-agent")
    print_result(result, as_json=ctx.obj.get("json", False))


@servers_guest_agent.command("status")
@click.argument("server_id")
@click.pass_context
def guest_agent_status(ctx: click.Context, server_id: str) -> None:
    """Get guest agent status."""
    client = build_client()
    result = client.request("GET", f"/servers/{_q(server_id)}/guest-agent/status")
    print_result(result, as_json=ctx.obj.get("json", False))


@servers_group.group("logs")
def servers_logs() -> None:
    """Server log operations."""


@servers_logs.command("list")
@click.argument("server_id")
@click.option("--page", type=int, default=None)
@click.option("--page-size", type=int, default=None)
@click.pass_context
def servers_logs_list(ctx: click.Context, server_id: str, page: int | None, page_size: int | None) -> None:
    """List server logs."""
    client = build_client()
    params = {}
    if page is not None:
        params["page"] = page
    if page_size is not None:
        params["pageSize"] = page_size
    result = client.request("GET", f"/servers/{_q(server_id)}/logs", params=params or None)
    print_result(result, as_json=ctx.obj.get("json", False))


@servers_group.group("rescue")
def servers_rescue() -> None:
    """Manage rescue mode."""


@servers_rescue.command("get")
@click.argument("server_id")
@click.pass_context
def rescue_get(ctx: click.Context, server_id: str) -> None:
    """Get rescue mode configuration."""
    client = build_client()
    result = client.request("GET", f"/servers/{_q(server_id)}/rescue")
    print_result(result, as_json=ctx.obj.get("json", False))


@servers_rescue.command("activate")
@click.argument("server_id")
@click.option("--yes", "-y", is_flag=True)
@click.pass_context
def rescue_activate(ctx: click.Context, server_id: str, yes: bool) -> None:
    """Activate rescue mode (interrupts the server)."""
    confirm_action(
        f"Activate rescue mode on server {server_id}? The server will be rebooted into rescue.",
        yes=yes,
        non_interactive_error="Rescue activation requires --yes for non-interactive use.",
    )
    client = build_client()
    result = client.request("POST", f"/servers/{_q(server_id)}/rescue/activate")
    print_result(result, as_json=ctx.obj.get("json", False))


@servers_rescue.command("deactivate")
@click.argument("server_id")
@click.option("--yes", "-y", is_flag=True)
@click.pass_context
def rescue_deactivate(ctx: click.Context, server_id: str, yes: bool) -> None:
    """Deactivate rescue mode."""
    confirm_action(
        f"Deactivate rescue mode on server {server_id}?",
        yes=yes,
    )
    client = build_client()
    result = client.request("POST", f"/servers/{_q(server_id)}/rescue/deactivate")
    print_result(result, as_json=ctx.obj.get("json", False))


@servers_group.group("storage")
def servers_storage() -> None:
    """Storage operations."""


@servers_storage.command("optimize")
@click.argument("server_id")
@click.pass_context
def storage_optimize(ctx: click.Context, server_id: str) -> None:
    """Optimize server storage."""
    client = build_client()
    result = client.request("POST", f"/servers/{_q(server_id)}/storage/optimize")
    print_result(result, as_json=ctx.obj.get("json", False))
