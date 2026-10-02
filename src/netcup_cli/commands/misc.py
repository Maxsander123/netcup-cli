from __future__ import annotations

import click

from netcup_cli.client import build_client
from netcup_cli.output import print_result, console


@click.group("api")
def api_group() -> None:
    """API utility operations."""


@api_group.command("ping")
@click.pass_context
def api_ping(ctx: click.Context) -> None:
    """Ping the SCP API to check connectivity."""
    client = build_client()
    result = client.request("GET", "/ping")
    print_result(result or {"status": "ok"}, as_json=ctx.obj.get("json", False))


@api_group.group("openapi")
def api_openapi() -> None:
    """OpenAPI schema operations."""


@api_openapi.command("get")
@click.pass_context
def api_openapi_get(ctx: click.Context) -> None:
    """Download the live OpenAPI schema from the SCP API."""
    client = build_client()
    result = client.request("GET", "/openapi")
    print_result(result, as_json=ctx.obj.get("json", False))


@api_openapi.command("explore")
@click.pass_context
def api_openapi_explore(ctx: click.Context) -> None:
    """List all operations in the OpenAPI schema."""
    client = build_client()
    spec = client.request("GET", "/openapi")
    if not isinstance(spec, dict):
        console.print("[yellow]No schema returned.[/yellow]")
        return
    rows = []
    for path, path_item in (spec.get("paths") or {}).items():
        for method in ("get", "post", "put", "patch", "delete"):
            if method in path_item:
                op = path_item[method]
                rows.append({
                    "method": method.upper(),
                    "path": path,
                    "operationId": op.get("operationId", ""),
                    "summary": op.get("summary", ""),
                })
    print_result(rows, as_json=ctx.obj.get("json", False))


@click.group("maintenance")
def maintenance_group() -> None:
    """Maintenance information. [deprecated: endpoint removed 2026-12-31]"""


@maintenance_group.command("info")
@click.pass_context
def maintenance_info(ctx: click.Context) -> None:
    """Get maintenance window information. [DEPRECATED: endpoint removed 2026-12-31]"""
    client = build_client()
    result = client.request("GET", "/maintenance")
    print_result(result, as_json=ctx.obj.get("json", False))
