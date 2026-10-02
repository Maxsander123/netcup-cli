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


def _uid(user_id: str | None) -> str:
    return _q(user_id) if user_id else "me"


@click.group("users")
def users_group() -> None:
    """Manage user account and resources."""


@users_group.command("get")
@click.argument("user_id", required=False, default=None)
@click.pass_context
def users_get(ctx: click.Context, user_id: str | None) -> None:
    """Get user details."""
    client = build_client()
    result = client.request("GET", f"/users/{_uid(user_id)}")
    print_result(result, as_json=ctx.obj.get("json", False))


@users_group.command("update")
@click.argument("user_id", required=False, default=None)
@click.option("--body-file", type=click.Path(exists=True), required=True)
@click.pass_context
def users_update(ctx: click.Context, user_id: str | None, body_file: str) -> None:
    """Update user details."""
    body = json.loads(open(body_file).read())
    client = build_client()
    result = client.request("PUT", f"/users/{_uid(user_id)}", json_body=body)
    print_result(result, as_json=ctx.obj.get("json", False))


@users_group.group("logs")
def users_logs() -> None:
    """User log operations."""


@users_logs.command("list")
@click.argument("user_id", required=False, default=None)
@click.option("--page", type=int, default=None)
@click.option("--page-size", type=int, default=None)
@click.pass_context
def users_logs_list(ctx: click.Context, user_id: str | None, page: int | None, page_size: int | None) -> None:
    """List user logs."""
    params = {}
    if page is not None:
        params["page"] = page
    if page_size is not None:
        params["pageSize"] = page_size
    client = build_client()
    result = client.request("GET", f"/users/{_uid(user_id)}/logs", params=params or None)
    print_result(result, as_json=ctx.obj.get("json", False))


@users_group.group("ssh-keys")
def users_ssh_keys() -> None:
    """Manage SSH keys."""


@users_ssh_keys.command("list")
@click.argument("user_id", required=False, default=None)
@click.pass_context
def ssh_keys_list(ctx: click.Context, user_id: str | None) -> None:
    """List SSH keys."""
    client = build_client()
    result = client.request("GET", f"/users/{_uid(user_id)}/ssh-keys")
    print_result(result, as_json=ctx.obj.get("json", False))


@users_ssh_keys.command("create")
@click.argument("user_id", required=False, default=None)
@click.option("--name", required=True)
@click.option("--public-key", required=True)
@click.pass_context
def ssh_keys_create(ctx: click.Context, user_id: str | None, name: str, public_key: str) -> None:
    """Add an SSH public key."""
    client = build_client()
    result = client.request("POST", f"/users/{_uid(user_id)}/ssh-keys", json_body={"name": name, "publicKey": public_key})
    print_result(result, as_json=ctx.obj.get("json", False))


@users_ssh_keys.command("delete")
@click.argument("user_id", required=False, default=None)
@click.argument("key_id")
@click.option("--yes", "-y", is_flag=True)
@click.pass_context
def ssh_keys_delete(ctx: click.Context, user_id: str | None, key_id: str, yes: bool) -> None:
    """Delete an SSH key. This may remove account access."""
    confirm_action(
        f"Delete SSH key {key_id}? This may remove access to servers using this key.",
        yes=yes,
        non_interactive_error="SSH key delete requires --yes for non-interactive use.",
    )
    client = build_client()
    result = client.request("DELETE", f"/users/{_uid(user_id)}/ssh-keys/{_q(key_id)}")
    print_result(result, as_json=ctx.obj.get("json", False))


@users_group.group("failover-ips")
def users_failover_ips() -> None:
    """Manage failover IPs."""


@users_failover_ips.group("ipv4")
def failover_ipv4() -> None:
    """IPv4 failover IP operations."""


@failover_ipv4.command("list")
@click.argument("user_id", required=False, default=None)
@click.pass_context
def failover_ipv4_list(ctx: click.Context, user_id: str | None) -> None:
    """List IPv4 failover IPs."""
    client = build_client()
    result = client.request("GET", f"/users/{_uid(user_id)}/failoverips/v4")
    print_result(result, as_json=ctx.obj.get("json", False))


@failover_ipv4.command("route")
@click.argument("user_id", required=False, default=None)
@click.argument("failover_ip_id")
@click.option("--server-id", required=True, help="Target server ID to route to.")
@click.option("--yes", "-y", is_flag=True)
@click.pass_context
def failover_ipv4_route(ctx: click.Context, user_id: str | None, failover_ip_id: str, server_id: str, yes: bool) -> None:
    """Route an IPv4 failover IP to a server."""
    confirm_action(
        f"Route failover IP {failover_ip_id} to server {server_id}? This may disrupt connectivity.",
        yes=yes,
    )
    client = build_client()
    result = client.request("PATCH", f"/users/{_uid(user_id)}/failoverips/v4/{_q(failover_ip_id)}", json_body={"serverId": server_id}, merge_patch=True)
    print_result(result, as_json=ctx.obj.get("json", False))


@users_failover_ips.group("ipv6")
def failover_ipv6() -> None:
    """IPv6 failover IP operations."""


@failover_ipv6.command("list")
@click.argument("user_id", required=False, default=None)
@click.pass_context
def failover_ipv6_list(ctx: click.Context, user_id: str | None) -> None:
    """List IPv6 failover IPs."""
    client = build_client()
    result = client.request("GET", f"/users/{_uid(user_id)}/failoverips/v6")
    print_result(result, as_json=ctx.obj.get("json", False))


@failover_ipv6.command("route")
@click.argument("user_id", required=False, default=None)
@click.argument("failover_ip_id")
@click.option("--server-id", required=True)
@click.option("--yes", "-y", is_flag=True)
@click.pass_context
def failover_ipv6_route(ctx: click.Context, user_id: str | None, failover_ip_id: str, server_id: str, yes: bool) -> None:
    """Route an IPv6 failover IP to a server."""
    confirm_action(
        f"Route failover IP {failover_ip_id} to server {server_id}? This may disrupt connectivity.",
        yes=yes,
    )
    client = build_client()
    result = client.request("PATCH", f"/users/{_uid(user_id)}/failoverips/v6/{_q(failover_ip_id)}", json_body={"serverId": server_id}, merge_patch=True)
    print_result(result, as_json=ctx.obj.get("json", False))


@users_group.group("firewall-policies")
def users_fw_policies() -> None:
    """Manage user firewall policies."""


@users_fw_policies.command("list")
@click.argument("user_id", required=False, default=None)
@click.pass_context
def fw_policies_list(ctx: click.Context, user_id: str | None) -> None:
    """List firewall policies."""
    client = build_client()
    result = client.request("GET", f"/users/{_uid(user_id)}/firewall-policies")
    print_result(result, as_json=ctx.obj.get("json", False))


@users_fw_policies.command("create")
@click.argument("user_id", required=False, default=None)
@click.option("--body-file", type=click.Path(exists=True), required=True)
@click.pass_context
def fw_policies_create(ctx: click.Context, user_id: str | None, body_file: str) -> None:
    """Create a firewall policy."""
    body = json.loads(open(body_file).read())
    client = build_client()
    result = client.request("POST", f"/users/{_uid(user_id)}/firewall-policies", json_body=body)
    print_result(result, as_json=ctx.obj.get("json", False))


@users_fw_policies.command("get")
@click.argument("user_id", required=False, default=None)
@click.argument("policy_id")
@click.pass_context
def fw_policies_get(ctx: click.Context, user_id: str | None, policy_id: str) -> None:
    """Get a firewall policy."""
    client = build_client()
    result = client.request("GET", f"/users/{_uid(user_id)}/firewall-policies/{_q(policy_id)}")
    print_result(result, as_json=ctx.obj.get("json", False))


@users_fw_policies.command("update")
@click.argument("user_id", required=False, default=None)
@click.argument("policy_id")
@click.option("--body-file", type=click.Path(exists=True), required=True)
@click.option("--yes", "-y", is_flag=True)
@click.pass_context
def fw_policies_update(ctx: click.Context, user_id: str | None, policy_id: str, body_file: str, yes: bool) -> None:
    """Update a firewall policy."""
    confirm_action(
        f"Update firewall policy {policy_id}? This may interrupt connectivity on attached interfaces.",
        yes=yes,
    )
    body = json.loads(open(body_file).read())
    client = build_client()
    result = client.request("PUT", f"/users/{_uid(user_id)}/firewall-policies/{_q(policy_id)}", json_body=body)
    print_result(result, as_json=ctx.obj.get("json", False))


@users_fw_policies.command("delete")
@click.argument("user_id", required=False, default=None)
@click.argument("policy_id")
@click.option("--yes", "-y", is_flag=True)
@click.pass_context
def fw_policies_delete(ctx: click.Context, user_id: str | None, policy_id: str, yes: bool) -> None:
    """Delete a firewall policy."""
    confirm_action(
        f"Delete firewall policy {policy_id}? This may interrupt connectivity on attached interfaces.",
        yes=yes,
        non_interactive_error="Firewall policy delete requires --yes for non-interactive use.",
    )
    client = build_client()
    result = client.request("DELETE", f"/users/{_uid(user_id)}/firewall-policies/{_q(policy_id)}")
    print_result(result, as_json=ctx.obj.get("json", False))


@users_group.group("images")
def users_images() -> None:
    """Manage user images."""


@users_images.command("list")
@click.argument("user_id", required=False, default=None)
@click.pass_context
def user_images_list(ctx: click.Context, user_id: str | None) -> None:
    """List user images."""
    client = build_client()
    result = client.request("GET", f"/users/{_uid(user_id)}/images")
    print_result(result, as_json=ctx.obj.get("json", False))


@users_images.command("get")
@click.argument("user_id", required=False, default=None)
@click.argument("image_id")
@click.pass_context
def user_images_get(ctx: click.Context, user_id: str | None, image_id: str) -> None:
    """Get a user image."""
    client = build_client()
    result = client.request("GET", f"/users/{_uid(user_id)}/images/{_q(image_id)}")
    print_result(result, as_json=ctx.obj.get("json", False))


@users_images.command("prepare-upload")
@click.argument("user_id", required=False, default=None)
@click.option("--key", required=True, help="Storage key/filename for the image.")
@click.option("--multipart/--single", default=True, show_default=True)
@click.pass_context
def user_images_prepare_upload(ctx: click.Context, user_id: str | None, key: str, multipart: bool) -> None:
    """Prepare an image upload (returns upload ID for multipart)."""
    client = build_client()
    result = client.request("POST", f"/users/{_uid(user_id)}/images/{_q(key)}", json_body={"multipart": multipart})
    print_result(result, as_json=ctx.obj.get("json", False))


@users_images.command("get-part-url")
@click.argument("user_id", required=False, default=None)
@click.option("--key", required=True, help="Image key.")
@click.option("--upload-id", required=True)
@click.option("--part-number", type=int, required=True)
@click.pass_context
def user_images_get_part_url(ctx: click.Context, user_id: str | None, key: str, upload_id: str, part_number: int) -> None:
    """Get a presigned URL for an image upload part."""
    client = build_client()
    result = client.request("GET", f"/users/{_uid(user_id)}/images/{_q(key)}/{_q(upload_id)}/parts/{part_number}")
    print_result(result, as_json=ctx.obj.get("json", False))


@users_images.command("complete-upload")
@click.argument("user_id", required=False, default=None)
@click.option("--key", required=True, help="Image key.")
@click.option("--upload-id", required=True)
@click.option("--body-file", type=click.Path(exists=True), required=True, help="JSON file with parts/ETags list.")
@click.pass_context
def user_images_complete_upload(ctx: click.Context, user_id: str | None, key: str, upload_id: str, body_file: str) -> None:
    """Complete a multipart image upload."""
    body = json.loads(open(body_file).read())
    client = build_client()
    result = client.request("PUT", f"/users/{_uid(user_id)}/images/{_q(key)}/{_q(upload_id)}", json_body=body)
    print_result(result, as_json=ctx.obj.get("json", False))


@users_images.command("delete")
@click.argument("user_id", required=False, default=None)
@click.argument("image_id")
@click.option("--yes", "-y", is_flag=True)
@click.pass_context
def user_images_delete(ctx: click.Context, user_id: str | None, image_id: str, yes: bool) -> None:
    """Delete a user image."""
    confirm_action(
        f"Delete user image {image_id}? This cannot be undone.",
        yes=yes,
        non_interactive_error="Image delete requires --yes for non-interactive use.",
    )
    client = build_client()
    result = client.request("DELETE", f"/users/{_uid(user_id)}/images/{_q(image_id)}")
    print_result(result, as_json=ctx.obj.get("json", False))


@users_images.command("upload")
@click.argument("user_id", required=False, default=None)
@click.option("--file", "file_path", type=click.Path(exists=True), required=True)
@click.option("--key", required=True)
@click.option("--multipart/--single", default=True, show_default=True)
@click.option("--part-size", type=int, default=67_108_864, show_default=True)
@click.pass_context
def user_images_upload(ctx: click.Context, user_id: str | None, file_path: str, key: str, multipart: bool, part_size: int) -> None:
    """Upload an image file (convenience command)."""
    uid = _uid(user_id)
    client = build_client()
    result = upload_file(client, resource="images", file_path=Path(file_path), key=key, user_id=uid, multipart=multipart, part_size=part_size)
    print_result(result, as_json=ctx.obj.get("json", False))


@users_group.group("isos")
def users_isos() -> None:
    """Manage user ISOs."""


@users_isos.command("list")
@click.argument("user_id", required=False, default=None)
@click.pass_context
def user_isos_list(ctx: click.Context, user_id: str | None) -> None:
    """List user ISOs."""
    client = build_client()
    result = client.request("GET", f"/users/{_uid(user_id)}/isos")
    print_result(result, as_json=ctx.obj.get("json", False))


@users_isos.command("get")
@click.argument("user_id", required=False, default=None)
@click.argument("iso_id")
@click.pass_context
def user_isos_get(ctx: click.Context, user_id: str | None, iso_id: str) -> None:
    """Get a user ISO."""
    client = build_client()
    result = client.request("GET", f"/users/{_uid(user_id)}/isos/{_q(iso_id)}")
    print_result(result, as_json=ctx.obj.get("json", False))


@users_isos.command("prepare-upload")
@click.argument("user_id", required=False, default=None)
@click.option("--key", required=True)
@click.option("--multipart/--single", default=True, show_default=True)
@click.pass_context
def user_isos_prepare_upload(ctx: click.Context, user_id: str | None, key: str, multipart: bool) -> None:
    """Prepare an ISO upload (returns upload ID for multipart)."""
    client = build_client()
    result = client.request("POST", f"/users/{_uid(user_id)}/isos/{_q(key)}", json_body={"multipart": multipart})
    print_result(result, as_json=ctx.obj.get("json", False))


@users_isos.command("get-part-url")
@click.argument("user_id", required=False, default=None)
@click.option("--key", required=True, help="ISO key.")
@click.option("--upload-id", required=True)
@click.option("--part-number", type=int, required=True)
@click.pass_context
def user_isos_get_part_url(ctx: click.Context, user_id: str | None, key: str, upload_id: str, part_number: int) -> None:
    """Get a presigned URL for an ISO upload part."""
    client = build_client()
    result = client.request("GET", f"/users/{_uid(user_id)}/isos/{_q(key)}/{_q(upload_id)}/parts/{part_number}")
    print_result(result, as_json=ctx.obj.get("json", False))


@users_isos.command("complete-upload")
@click.argument("user_id", required=False, default=None)
@click.option("--key", required=True, help="ISO key.")
@click.option("--upload-id", required=True)
@click.option("--body-file", type=click.Path(exists=True), required=True)
@click.pass_context
def user_isos_complete_upload(ctx: click.Context, user_id: str | None, key: str, upload_id: str, body_file: str) -> None:
    """Complete a multipart ISO upload."""
    body = json.loads(open(body_file).read())
    client = build_client()
    result = client.request("PUT", f"/users/{_uid(user_id)}/isos/{_q(key)}/{_q(upload_id)}", json_body=body)
    print_result(result, as_json=ctx.obj.get("json", False))


@users_isos.command("delete")
@click.argument("user_id", required=False, default=None)
@click.argument("iso_id")
@click.option("--yes", "-y", is_flag=True)
@click.pass_context
def user_isos_delete(ctx: click.Context, user_id: str | None, iso_id: str, yes: bool) -> None:
    """Delete a user ISO."""
    confirm_action(
        f"Delete user ISO {iso_id}? This cannot be undone.",
        yes=yes,
        non_interactive_error="ISO delete requires --yes for non-interactive use.",
    )
    client = build_client()
    result = client.request("DELETE", f"/users/{_uid(user_id)}/isos/{_q(iso_id)}")
    print_result(result, as_json=ctx.obj.get("json", False))


@users_isos.command("upload")
@click.argument("user_id", required=False, default=None)
@click.option("--file", "file_path", type=click.Path(exists=True), required=True)
@click.option("--key", required=True)
@click.option("--multipart/--single", default=True, show_default=True)
@click.option("--part-size", type=int, default=67_108_864, show_default=True)
@click.pass_context
def user_isos_upload(ctx: click.Context, user_id: str | None, file_path: str, key: str, multipart: bool, part_size: int) -> None:
    """Upload an ISO file (convenience command)."""
    uid = _uid(user_id)
    client = build_client()
    result = upload_file(client, resource="isos", file_path=Path(file_path), key=key, user_id=uid, multipart=multipart, part_size=part_size)
    print_result(result, as_json=ctx.obj.get("json", False))


@users_group.group("vlans")
def users_vlans() -> None:
    """Manage user VLANs."""


@users_vlans.command("list")
@click.argument("user_id", required=False, default=None)
@click.pass_context
def user_vlans_list(ctx: click.Context, user_id: str | None) -> None:
    """List user VLANs."""
    client = build_client()
    result = client.request("GET", f"/users/{_uid(user_id)}/vlans")
    print_result(result, as_json=ctx.obj.get("json", False))


@users_vlans.command("get")
@click.argument("user_id", required=False, default=None)
@click.argument("vlan_id")
@click.pass_context
def user_vlans_get(ctx: click.Context, user_id: str | None, vlan_id: str) -> None:
    """Get a user VLAN."""
    client = build_client()
    result = client.request("GET", f"/users/{_uid(user_id)}/vlans/{_q(vlan_id)}")
    print_result(result, as_json=ctx.obj.get("json", False))


@users_vlans.command("update")
@click.argument("user_id", required=False, default=None)
@click.argument("vlan_id")
@click.option("--body-file", type=click.Path(exists=True), required=True)
@click.option("--yes", "-y", is_flag=True)
@click.pass_context
def user_vlans_update(ctx: click.Context, user_id: str | None, vlan_id: str, body_file: str, yes: bool) -> None:
    """Update a user VLAN."""
    confirm_action(
        f"Update VLAN {vlan_id}? This may disrupt connectivity.",
        yes=yes,
    )
    body = json.loads(open(body_file).read())
    client = build_client()
    result = client.request("PUT", f"/users/{_uid(user_id)}/vlans/{_q(vlan_id)}", json_body=body)
    print_result(result, as_json=ctx.obj.get("json", False))
