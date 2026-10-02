from __future__ import annotations

import json
from urllib.parse import quote

import click

from netcup_cli.client import build_client
from netcup_cli.output import print_result
from netcup_cli.safety import confirm_action


def _q(s: str) -> str:
    return quote(str(s), safe="")


@click.group("interfaces")
def server_interfaces_group() -> None:
    """Manage server network interfaces."""


@server_interfaces_group.command("list")
@click.argument("server_id")
@click.pass_context
def ifaces_list(ctx: click.Context, server_id: str) -> None:
    """List interfaces on a server."""
    client = build_client()
    result = client.request("GET", f"/servers/{_q(server_id)}/interfaces")
    print_result(result, as_json=ctx.obj.get("json", False))


@server_interfaces_group.command("create")
@click.argument("server_id")
@click.option("--body-file", type=click.Path(exists=True), required=True)
@click.pass_context
def ifaces_create(ctx: click.Context, server_id: str, body_file: str) -> None:
    """Create a network interface on a server."""
    body = json.loads(open(body_file).read())
    client = build_client()
    result = client.request("POST", f"/servers/{_q(server_id)}/interfaces", json_body=body)
    print_result(result, as_json=ctx.obj.get("json", False))


@server_interfaces_group.command("get")
@click.argument("server_id")
@click.argument("interface_id")
@click.pass_context
def ifaces_get(ctx: click.Context, server_id: str, interface_id: str) -> None:
    """Get a specific interface."""
    client = build_client()
    result = client.request("GET", f"/servers/{_q(server_id)}/interfaces/{_q(interface_id)}")
    print_result(result, as_json=ctx.obj.get("json", False))


@server_interfaces_group.command("update")
@click.argument("server_id")
@click.argument("interface_id")
@click.option("--body-file", type=click.Path(exists=True), required=True)
@click.option("--yes", "-y", is_flag=True)
@click.pass_context
def ifaces_update(ctx: click.Context, server_id: str, interface_id: str, body_file: str, yes: bool) -> None:
    """Update a network interface."""
    confirm_action(
        f"Update interface {interface_id} on server {server_id}? This may disrupt connectivity.",
        yes=yes,
    )
    body = json.loads(open(body_file).read())
    client = build_client()
    result = client.request("PATCH", f"/servers/{_q(server_id)}/interfaces/{_q(interface_id)}", json_body=body)
    print_result(result, as_json=ctx.obj.get("json", False))


@server_interfaces_group.command("delete")
@click.argument("server_id")
@click.argument("interface_id")
@click.option("--yes", "-y", is_flag=True)
@click.pass_context
def ifaces_delete(ctx: click.Context, server_id: str, interface_id: str, yes: bool) -> None:
    """Delete a network interface. This will disrupt connectivity on that interface."""
    confirm_action(
        f"Delete interface {interface_id} on server {server_id}? This will disrupt connectivity.",
        yes=yes,
        non_interactive_error="Interface delete requires --yes for non-interactive use.",
    )
    client = build_client()
    result = client.request("DELETE", f"/servers/{_q(server_id)}/interfaces/{_q(interface_id)}")
    print_result(result, as_json=ctx.obj.get("json", False))


@server_interfaces_group.group("firewall")
def iface_firewall_group() -> None:
    """Manage per-interface firewall rules."""


@iface_firewall_group.command("get")
@click.argument("server_id")
@click.argument("interface_id")
@click.pass_context
def iface_fw_get(ctx: click.Context, server_id: str, interface_id: str) -> None:
    """Get firewall rules for an interface."""
    client = build_client()
    result = client.request("GET", f"/servers/{_q(server_id)}/interfaces/{_q(interface_id)}/firewall")
    print_result(result, as_json=ctx.obj.get("json", False))


@iface_firewall_group.command("update")
@click.argument("server_id")
@click.argument("interface_id")
@click.option("--body-file", type=click.Path(exists=True), required=True)
@click.option("--yes", "-y", is_flag=True)
@click.pass_context
def iface_fw_update(ctx: click.Context, server_id: str, interface_id: str, body_file: str, yes: bool) -> None:
    """Update firewall rules for an interface."""
    confirm_action(
        f"Update firewall on interface {interface_id} (server {server_id})? This may interrupt connectivity.",
        yes=yes,
        non_interactive_error="Firewall update requires --yes for non-interactive use.",
    )
    body = json.loads(open(body_file).read())
    client = build_client()
    result = client.request("PUT", f"/servers/{_q(server_id)}/interfaces/{_q(interface_id)}/firewall", json_body=body)
    print_result(result, as_json=ctx.obj.get("json", False))


@iface_firewall_group.command("reapply")
@click.argument("server_id")
@click.argument("interface_id")
@click.option("--yes", "-y", is_flag=True)
@click.pass_context
def iface_fw_reapply(ctx: click.Context, server_id: str, interface_id: str, yes: bool) -> None:
    """Reapply firewall rules for an interface."""
    confirm_action(
        f"Reapply firewall on interface {interface_id} (server {server_id})?",
        yes=yes,
    )
    client = build_client()
    result = client.request("POST", f"/servers/{_q(server_id)}/interfaces/{_q(interface_id)}/firewall/reapply")
    print_result(result, as_json=ctx.obj.get("json", False))


@iface_firewall_group.command("restore-copied-policies")
@click.argument("server_id")
@click.argument("interface_id")
@click.option("--yes", "-y", is_flag=True)
@click.pass_context
def iface_fw_restore_policies(ctx: click.Context, server_id: str, interface_id: str, yes: bool) -> None:
    """Restore copied firewall policies for an interface."""
    confirm_action(
        f"Restore copied firewall policies on interface {interface_id} (server {server_id})? This may interrupt connectivity.",
        yes=yes,
        non_interactive_error="Policy restore requires --yes for non-interactive use.",
    )
    client = build_client()
    result = client.request("POST", f"/servers/{_q(server_id)}/interfaces/{_q(interface_id)}/firewall/restore-copied-policies")
    print_result(result, as_json=ctx.obj.get("json", False))


@click.group("rdns")
def rdns_group() -> None:
    """Manage reverse DNS entries."""


@rdns_group.group("ipv4")
def rdns_ipv4() -> None:
    """IPv4 reverse DNS operations."""


@rdns_ipv4.command("get")
@click.argument("ip")
@click.pass_context
def rdns_ipv4_get(ctx: click.Context, ip: str) -> None:
    """Get rDNS for an IPv4 address."""
    client = build_client()
    result = client.request("GET", f"/rdns/ipv4/{_q(ip)}")
    print_result(result, as_json=ctx.obj.get("json", False))


@rdns_ipv4.command("set")
@click.argument("ip")
@click.option("--hostname", required=True)
@click.pass_context
def rdns_ipv4_set(ctx: click.Context, ip: str, hostname: str) -> None:
    """Set rDNS for an IPv4 address."""
    client = build_client()
    result = client.request("PUT", f"/rdns/ipv4/{_q(ip)}", json_body={"hostname": hostname})
    print_result(result, as_json=ctx.obj.get("json", False))


@rdns_ipv4.command("delete")
@click.argument("ip")
@click.pass_context
def rdns_ipv4_delete(ctx: click.Context, ip: str) -> None:
    """Delete rDNS for an IPv4 address."""
    client = build_client()
    result = client.request("DELETE", f"/rdns/ipv4/{_q(ip)}")
    print_result(result, as_json=ctx.obj.get("json", False))


@rdns_group.group("ipv6")
def rdns_ipv6() -> None:
    """IPv6 reverse DNS operations."""


@rdns_ipv6.command("get")
@click.argument("ip")
@click.pass_context
def rdns_ipv6_get(ctx: click.Context, ip: str) -> None:
    """Get rDNS for an IPv6 address."""
    client = build_client()
    result = client.request("GET", f"/rdns/ipv6/{_q(ip)}")
    print_result(result, as_json=ctx.obj.get("json", False))


@rdns_ipv6.command("set")
@click.argument("ip")
@click.option("--hostname", required=True)
@click.pass_context
def rdns_ipv6_set(ctx: click.Context, ip: str, hostname: str) -> None:
    """Set rDNS for an IPv6 address."""
    client = build_client()
    result = client.request("PUT", f"/rdns/ipv6/{_q(ip)}", json_body={"hostname": hostname})
    print_result(result, as_json=ctx.obj.get("json", False))


@rdns_ipv6.command("delete")
@click.argument("ip")
@click.pass_context
def rdns_ipv6_delete(ctx: click.Context, ip: str) -> None:
    """Delete rDNS for an IPv6 address."""
    client = build_client()
    result = client.request("DELETE", f"/rdns/ipv6/{_q(ip)}")
    print_result(result, as_json=ctx.obj.get("json", False))


@click.group("vlans")
def vlans_group() -> None:
    """Manage VLANs."""


@vlans_group.command("get")
@click.argument("vlan_id")
@click.pass_context
def vlans_get(ctx: click.Context, vlan_id: str) -> None:
    """Get a VLAN by ID."""
    client = build_client()
    result = client.request("GET", f"/vlans/{_q(vlan_id)}")
    print_result(result, as_json=ctx.obj.get("json", False))
