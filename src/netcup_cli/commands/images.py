from __future__ import annotations

from urllib.parse import quote

import click

from netcup_cli.client import build_client, resolve_server
from netcup_cli.errors import CLIError
from netcup_cli.output import print_result
from netcup_cli.safety import confirm_action


def _q(s: str) -> str:
    return quote(str(s), safe="")


@click.command("user-image")
@click.argument("server")
@click.argument("image_name")
@click.option("--disk", "disk_name", default=None, help="Target disk (default: first disk).")
@click.option("--send-email", is_flag=True, default=False)
@click.option("--yes", "-y", is_flag=True)
@click.pass_context
def server_user_image(ctx: click.Context, server: str, image_name: str, disk_name: str | None, send_email: bool, yes: bool) -> None:
    """Install one of your uploaded images (see 'users images list'). WARNING: formats the disk."""
    client = build_client()
    server_id = resolve_server(client, server)
    confirm_action(
        f"Install user image '{image_name}' on {server} ({server_id})? The disk will be FORMATTED.",
        yes=yes,
        non_interactive_error="User image install requires --yes for non-interactive use.",
    )
    body: dict = {"userImageName": image_name, "emailNotification": send_email}
    if disk_name:
        body["diskName"] = disk_name
    result = client.request("POST", f"/servers/{_q(server_id)}/user-image", json_body=body)
    print_result(result, as_json=ctx.obj.get("json", False))


@click.group("iso")
def server_iso_group() -> None:
    """Attach/detach ISO images."""


@server_iso_group.command("status")
@click.argument("server")
@click.pass_context
def iso_status(ctx: click.Context, server: str) -> None:
    """Show the currently attached ISO."""
    client = build_client()
    result = client.request("GET", f"/servers/{_q(resolve_server(client, server))}/iso")
    print_result(result, as_json=ctx.obj.get("json", False))


@server_iso_group.command("list")
@click.argument("server")
@click.pass_context
def iso_list(ctx: click.Context, server: str) -> None:
    """List ISOs provided by netcup for this server."""
    client = build_client()
    result = client.request("GET", f"/servers/{_q(resolve_server(client, server))}/isoimages")
    print_result(result, as_json=ctx.obj.get("json", False))


@server_iso_group.command("attach")
@click.argument("server")
@click.option("--iso-id", type=int, default=None, help="netcup ISO ID (from 'servers iso list').")
@click.option("--user-iso", default=None, help="Name of an uploaded ISO (from 'users isos list').")
@click.option("--boot/--no-boot", default=False, help="Change boot device to CD-ROM.")
@click.pass_context
def iso_attach(ctx: click.Context, server: str, iso_id: int | None, user_iso: str | None, boot: bool) -> None:
    """Attach an ISO to a server."""
    if (iso_id is None) == (user_iso is None):
        raise CLIError("Specify exactly one of --iso-id or --user-iso.")
    body: dict = {"changeBootDeviceToCdrom": boot}
    if iso_id is not None:
        body["isoId"] = iso_id
    else:
        body["userIsoName"] = user_iso
    client = build_client()
    result = client.request("POST", f"/servers/{_q(resolve_server(client, server))}/iso", json_body=body)
    print_result(result, as_json=ctx.obj.get("json", False))


@server_iso_group.command("detach")
@click.argument("server")
@click.pass_context
def iso_detach(ctx: click.Context, server: str) -> None:
    """Detach the current ISO."""
    client = build_client()
    result = client.request("DELETE", f"/servers/{_q(resolve_server(client, server))}/iso")
    print_result(result, as_json=ctx.obj.get("json", False))
