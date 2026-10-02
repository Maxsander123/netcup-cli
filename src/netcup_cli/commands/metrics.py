from __future__ import annotations

from urllib.parse import quote

import click

from netcup_cli.client import build_client
from netcup_cli.output import print_result


def _q(s: str) -> str:
    return quote(str(s), safe="")


def _metrics_options(fn):
    fn = click.option("--from", "from_time", default=None, help="Start time (ISO 8601).")(fn)
    fn = click.option("--to", "to_time", default=None, help="End time (ISO 8601).")(fn)
    fn = click.option("--resolution", default=None, help="Resolution (e.g. 1h, 1d).")(fn)
    return fn


@click.group("metrics")
def metrics_group() -> None:
    """Retrieve server performance metrics."""


@metrics_group.command("cpu")
@click.argument("server_id")
@_metrics_options
@click.pass_context
def metrics_cpu(ctx: click.Context, server_id: str, from_time: str | None, to_time: str | None, resolution: str | None) -> None:
    """Get CPU metrics for a server."""
    params = {k: v for k, v in {"from": from_time, "to": to_time, "resolution": resolution}.items() if v}
    client = build_client()
    result = client.request("GET", f"/servers/{_q(server_id)}/metrics/cpu", params=params or None)
    print_result(result, as_json=ctx.obj.get("json", False))


@metrics_group.command("disk")
@click.argument("server_id")
@_metrics_options
@click.pass_context
def metrics_disk(ctx: click.Context, server_id: str, from_time: str | None, to_time: str | None, resolution: str | None) -> None:
    """Get disk metrics for a server."""
    params = {k: v for k, v in {"from": from_time, "to": to_time, "resolution": resolution}.items() if v}
    client = build_client()
    result = client.request("GET", f"/servers/{_q(server_id)}/metrics/disk", params=params or None)
    print_result(result, as_json=ctx.obj.get("json", False))


@metrics_group.command("network")
@click.argument("server_id")
@_metrics_options
@click.pass_context
def metrics_network(ctx: click.Context, server_id: str, from_time: str | None, to_time: str | None, resolution: str | None) -> None:
    """Get network throughput metrics for a server."""
    params = {k: v for k, v in {"from": from_time, "to": to_time, "resolution": resolution}.items() if v}
    client = build_client()
    result = client.request("GET", f"/servers/{_q(server_id)}/metrics/network", params=params or None)
    print_result(result, as_json=ctx.obj.get("json", False))


@metrics_group.command("network-packets")
@click.argument("server_id")
@_metrics_options
@click.pass_context
def metrics_network_packets(ctx: click.Context, server_id: str, from_time: str | None, to_time: str | None, resolution: str | None) -> None:
    """Get network packet metrics for a server."""
    params = {k: v for k, v in {"from": from_time, "to": to_time, "resolution": resolution}.items() if v}
    client = build_client()
    result = client.request("GET", f"/servers/{_q(server_id)}/metrics/network-packets", params=params or None)
    print_result(result, as_json=ctx.obj.get("json", False))
