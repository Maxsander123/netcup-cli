from __future__ import annotations

import json
from urllib.parse import quote

import click

from netcup_cli.client import build_client
from netcup_cli.output import print_result
from netcup_cli.safety import confirm_action


def _q(s: str) -> str:
    return quote(str(s), safe="")


@click.group("disks")
def disks_group() -> None:
    """Manage server disks."""


@disks_group.command("list")
@click.argument("server_id")
@click.pass_context
def disks_list(ctx: click.Context, server_id: str) -> None:
    """List disks for a server."""
    client = build_client()
    result = client.request("GET", f"/servers/{_q(server_id)}/disks")
    print_result(result, as_json=ctx.obj.get("json", False))


@disks_group.command("get")
@click.argument("server_id")
@click.argument("disk_id")
@click.pass_context
def disks_get(ctx: click.Context, server_id: str, disk_id: str) -> None:
    """Get details of a specific disk."""
    client = build_client()
    result = client.request("GET", f"/servers/{_q(server_id)}/disks/{_q(disk_id)}")
    print_result(result, as_json=ctx.obj.get("json", False))


@disks_group.command("update")
@click.argument("server_id")
@click.argument("disk_id")
@click.option("--body-file", type=click.Path(exists=True), required=True, help="JSON file with update payload.")
@click.pass_context
def disks_update(ctx: click.Context, server_id: str, disk_id: str, body_file: str) -> None:
    """Update a disk."""
    body = json.loads(open(body_file).read())
    client = build_client()
    result = client.request("PATCH", f"/servers/{_q(server_id)}/disks/{_q(disk_id)}", json_body=body)
    print_result(result, as_json=ctx.obj.get("json", False))


@disks_group.command("supported-drivers")
@click.argument("server_id")
@click.pass_context
def disks_supported_drivers(ctx: click.Context, server_id: str) -> None:
    """List supported disk drivers for a server."""
    client = build_client()
    result = client.request("GET", f"/servers/{_q(server_id)}/disks/supported-drivers")
    print_result(result, as_json=ctx.obj.get("json", False))


@disks_group.command("format")
@click.argument("server_id")
@click.argument("disk_id")
@click.option("--filesystem", required=True, help="Target filesystem (e.g. ext4, xfs).")
@click.option("--yes", "-y", is_flag=True)
@click.pass_context
def disks_format(ctx: click.Context, server_id: str, disk_id: str, filesystem: str, yes: bool) -> None:
    """Format a disk. WARNING: destroys all data on the disk."""
    confirm_action(
        f"Format disk {disk_id} on server {server_id} with {filesystem}? All data will be lost.",
        yes=yes,
        non_interactive_error="Disk format requires --yes for non-interactive use.",
    )
    client = build_client()
    result = client.request("POST", f"/servers/{_q(server_id)}/disks/{_q(disk_id)}/format", json_body={"filesystem": filesystem})
    print_result(result, as_json=ctx.obj.get("json", False))
