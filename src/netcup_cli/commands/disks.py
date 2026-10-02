from __future__ import annotations

from urllib.parse import quote

import click

from netcup_cli.client import build_client, resolve_server
from netcup_cli.output import print_result
from netcup_cli.safety import confirm_action


def _q(s: str) -> str:
    return quote(str(s), safe="")


@click.group("disks")
def disks_group() -> None:
    """Manage server disks."""


@disks_group.command("list")
@click.argument("server")
@click.pass_context
def disks_list(ctx: click.Context, server: str) -> None:
    """List disks of a server."""
    client = build_client()
    result = client.request("GET", f"/servers/{_q(resolve_server(client, server))}/disks")
    print_result(result, as_json=ctx.obj.get("json", False))


@disks_group.command("get")
@click.argument("server")
@click.argument("disk_name")
@click.pass_context
def disks_get(ctx: click.Context, server: str, disk_name: str) -> None:
    """Get a disk by name (e.g. vda)."""
    client = build_client()
    result = client.request("GET", f"/servers/{_q(resolve_server(client, server))}/disks/{_q(disk_name)}")
    print_result(result, as_json=ctx.obj.get("json", False))


@disks_group.command("supported-drivers")
@click.argument("server")
@click.pass_context
def disks_supported_drivers(ctx: click.Context, server: str) -> None:
    """List supported disk drivers."""
    client = build_client()
    result = client.request("GET", f"/servers/{_q(resolve_server(client, server))}/disks/supported-drivers")
    print_result(result, as_json=ctx.obj.get("json", False))


@disks_group.command("set-driver")
@click.argument("server")
@click.argument("driver")
@click.option("--yes", "-y", is_flag=True)
@click.pass_context
def disks_set_driver(ctx: click.Context, server: str, driver: str, yes: bool) -> None:
    """Change the disk driver for all disks (e.g. VIRTIO, VIRTIO_SCSI, IDE, SATA)."""
    client = build_client()
    server_id = resolve_server(client, server)
    confirm_action(f"Change disk driver of {server} ({server_id}) to {driver}?", yes=yes)
    result = client.request(
        "PATCH", f"/servers/{_q(server_id)}/disks", json_body={"driver": driver.upper()}, merge_patch=True
    )
    print_result(result, as_json=ctx.obj.get("json", False))


@disks_group.command("format")
@click.argument("server")
@click.argument("disk_name")
@click.option("--yes", "-y", is_flag=True)
@click.pass_context
def disks_format(ctx: click.Context, server: str, disk_name: str, yes: bool) -> None:
    """Format a disk. WARNING: destroys all data on the disk."""
    client = build_client()
    server_id = resolve_server(client, server)
    confirm_action(
        f"Format disk {disk_name} on {server} ({server_id})? ALL DATA WILL BE LOST.",
        yes=yes,
        non_interactive_error="Disk format requires --yes for non-interactive use.",
    )
    result = client.request("POST", f"/servers/{_q(server_id)}/disks/{_q(disk_name)}:format")
    print_result(result, as_json=ctx.obj.get("json", False))
