from __future__ import annotations

from urllib.parse import quote

import click
from rich import box
from rich.table import Table

from netcup_cli.client import build_client, resolve_server
from netcup_cli.output import console, print_result


def _q(s: str) -> str:
    return quote(str(s), safe="")


def _show(ctx: click.Context, server: str, path: str, hours: int, last: int) -> None:
    client = build_client()
    result = client.request(
        "GET", f"/servers/{_q(resolve_server(client, server))}/metrics/{path}", params={"hours": hours}
    )
    if ctx.obj.get("json") or not isinstance(result, dict) or not result:
        print_result(result, as_json=ctx.obj.get("json", False))
        return
    # Response: {timestamp: {series: value}}
    rows = sorted(result.items())[-last:]
    series = sorted({k for _, v in rows if isinstance(v, dict) for k in v})
    t = Table(box=box.ROUNDED, title=f"{path} — last {hours}h")
    t.add_column("Time", style="cyan", no_wrap=True)
    for s in series:
        t.add_column(str(s), justify="right")
    for ts, vals in rows:
        vals = vals if isinstance(vals, dict) else {}
        t.add_row(ts[:16].replace("T", " "), *(f"{vals[s]:.2f}" if isinstance(vals.get(s), (int, float)) else "—" for s in series))
    console.print(t)


def _opts(fn):
    fn = click.option("--hours", type=int, default=1, show_default=True, help="Time window in hours.")(fn)
    fn = click.option("--last", type=int, default=15, show_default=True, help="Show only the last N data points.")(fn)
    return click.argument("server")(fn)


@click.group("metrics")
def metrics_group() -> None:
    """Server performance metrics."""


@metrics_group.command("cpu")
@_opts
@click.pass_context
def metrics_cpu(ctx: click.Context, server: str, hours: int, last: int) -> None:
    """CPU utilisation."""
    _show(ctx, server, "cpu", hours, last)


@metrics_group.command("disk")
@_opts
@click.pass_context
def metrics_disk(ctx: click.Context, server: str, hours: int, last: int) -> None:
    """Disk I/O."""
    _show(ctx, server, "disk", hours, last)


@metrics_group.command("network")
@_opts
@click.pass_context
def metrics_network(ctx: click.Context, server: str, hours: int, last: int) -> None:
    """Network throughput."""
    _show(ctx, server, "network", hours, last)


@metrics_group.command("packets")
@_opts
@click.pass_context
def metrics_packets(ctx: click.Context, server: str, hours: int, last: int) -> None:
    """Network packets."""
    _show(ctx, server, "network/packet", hours, last)
