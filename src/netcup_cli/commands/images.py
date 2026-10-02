from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import quote

import click

from netcup_cli.client import build_client
from netcup_cli.output import print_result
from netcup_cli.safety import confirm_action
from netcup_cli.uploads import upload_file


def _q(s: str) -> str:
    return quote(str(s), safe="")


@click.group("image")
def server_image_group() -> None:
    """Manage server images."""


@server_image_group.command("flavours")
@click.argument("server_id")
@click.pass_context
def image_flavours(ctx: click.Context, server_id: str) -> None:
    """List available image flavours for a server."""
    client = build_client()
    result = client.request("GET", f"/servers/{_q(server_id)}/imageflavours")
    print_result(result, as_json=ctx.obj.get("json", False))


@server_image_group.command("install-user")
@click.argument("server_id")
@click.option("--image-key", required=True, help="Key/ID of the user image to install.")
@click.option("--yes", "-y", is_flag=True)
@click.pass_context
def image_install_user(ctx: click.Context, server_id: str, image_key: str, yes: bool) -> None:
    """Install a user-provided image on a server. WARNING: formats the target disk."""
    confirm_action(
        f"Install user image {image_key} on server {server_id}? The target disk will be formatted.",
        yes=yes,
        non_interactive_error="User image install requires --yes for non-interactive use.",
    )
    client = build_client()
    result = client.request("POST", f"/servers/{_q(server_id)}/user-image", json_body={"key": image_key})
    print_result(result, as_json=ctx.obj.get("json", False))


@click.group("iso")
def server_iso_group() -> None:
    """Manage ISOs attached to a server."""


@server_iso_group.command("get")
@click.argument("server_id")
@click.pass_context
def iso_get(ctx: click.Context, server_id: str) -> None:
    """Get currently attached ISO."""
    client = build_client()
    result = client.request("GET", f"/servers/{_q(server_id)}/iso")
    print_result(result, as_json=ctx.obj.get("json", False))


@server_iso_group.command("attach")
@click.argument("server_id")
@click.option("--iso-key", required=True, help="ISO key (from 'servers iso list-available').")
@click.pass_context
def iso_attach(ctx: click.Context, server_id: str, iso_key: str) -> None:
    """Attach an ISO to a server."""
    client = build_client()
    result = client.request("POST", f"/servers/{_q(server_id)}/iso", json_body={"key": iso_key})
    print_result(result, as_json=ctx.obj.get("json", False))


@server_iso_group.command("detach")
@click.argument("server_id")
@click.option("--yes", "-y", is_flag=True)
@click.pass_context
def iso_detach(ctx: click.Context, server_id: str, yes: bool) -> None:
    """Detach the current ISO from a server."""
    confirm_action(f"Detach ISO from server {server_id}?", yes=yes)
    client = build_client()
    result = client.request("DELETE", f"/servers/{_q(server_id)}/iso")
    print_result(result, as_json=ctx.obj.get("json", False))


@server_iso_group.command("list-available")
@click.argument("server_id")
@click.pass_context
def iso_available(ctx: click.Context, server_id: str) -> None:
    """List available ISOs for a server."""
    client = build_client()
    result = client.request("GET", f"/servers/{_q(server_id)}/isoimages")
    print_result(result, as_json=ctx.obj.get("json", False))


@click.group("snapshots")
def server_snapshots_group() -> None:
    """Manage server snapshots."""


@server_snapshots_group.command("list")
@click.argument("server_id")
@click.pass_context
def snapshots_list(ctx: click.Context, server_id: str) -> None:
    """List snapshots for a server."""
    client = build_client()
    result = client.request("GET", f"/servers/{_q(server_id)}/snapshots")
    print_result(result, as_json=ctx.obj.get("json", False))


@server_snapshots_group.command("create")
@click.argument("server_id")
@click.option("--name", required=True)
@click.option("--description", default=None)
@click.pass_context
def snapshots_create(ctx: click.Context, server_id: str, name: str, description: str | None) -> None:
    """Create a snapshot."""
    body: dict = {"name": name}
    if description:
        body["description"] = description
    client = build_client()
    result = client.request("POST", f"/servers/{_q(server_id)}/snapshots", json_body=body)
    print_result(result, as_json=ctx.obj.get("json", False))


@server_snapshots_group.command("get")
@click.argument("server_id")
@click.argument("snapshot_id")
@click.pass_context
def snapshots_get(ctx: click.Context, server_id: str, snapshot_id: str) -> None:
    """Get a snapshot."""
    client = build_client()
    result = client.request("GET", f"/servers/{_q(server_id)}/snapshots/{_q(snapshot_id)}")
    print_result(result, as_json=ctx.obj.get("json", False))


@server_snapshots_group.command("delete")
@click.argument("server_id")
@click.argument("snapshot_id")
@click.option("--yes", "-y", is_flag=True)
@click.pass_context
def snapshots_delete(ctx: click.Context, server_id: str, snapshot_id: str, yes: bool) -> None:
    """Delete a snapshot. This cannot be undone."""
    confirm_action(
        f"Delete snapshot {snapshot_id} from server {server_id}? This cannot be undone.",
        yes=yes,
        non_interactive_error="Snapshot delete requires --yes for non-interactive use.",
    )
    client = build_client()
    result = client.request("DELETE", f"/servers/{_q(server_id)}/snapshots/{_q(snapshot_id)}")
    print_result(result, as_json=ctx.obj.get("json", False))


@server_snapshots_group.command("export")
@click.argument("server_id")
@click.argument("snapshot_id")
@click.pass_context
def snapshots_export(ctx: click.Context, server_id: str, snapshot_id: str) -> None:
    """Export a snapshot."""
    client = build_client()
    result = client.request("POST", f"/servers/{_q(server_id)}/snapshots/{_q(snapshot_id)}/export")
    print_result(result, as_json=ctx.obj.get("json", False))


@server_snapshots_group.command("revert")
@click.argument("server_id")
@click.argument("snapshot_id")
@click.option("--yes", "-y", is_flag=True)
@click.pass_context
def snapshots_revert(ctx: click.Context, server_id: str, snapshot_id: str, yes: bool) -> None:
    """Revert a server to a snapshot. WARNING: all data since the snapshot will be lost."""
    confirm_action(
        f"Revert server {server_id} to snapshot {snapshot_id}? All data since the snapshot will be lost.",
        yes=yes,
        non_interactive_error="Snapshot revert requires --yes for non-interactive use.",
    )
    client = build_client()
    result = client.request("POST", f"/servers/{_q(server_id)}/snapshots/{_q(snapshot_id)}/revert")
    print_result(result, as_json=ctx.obj.get("json", False))


@server_snapshots_group.command("dry-run")
@click.argument("server_id")
@click.pass_context
def snapshots_dry_run(ctx: click.Context, server_id: str) -> None:
    """Dry-run snapshot creation to check compatibility."""
    client = build_client()
    result = client.request("POST", f"/servers/{_q(server_id)}/snapshots:dryrun")
    print_result(result, as_json=ctx.obj.get("json", False))
