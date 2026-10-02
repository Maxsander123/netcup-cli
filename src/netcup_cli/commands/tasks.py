from __future__ import annotations

from urllib.parse import quote

import click

from netcup_cli.client import build_client
from netcup_cli.output import print_result
from netcup_cli.safety import confirm_action


def _q(s: str) -> str:
    return quote(str(s), safe="")


@click.group("tasks")
def tasks_group() -> None:
    """Manage asynchronous tasks."""


@tasks_group.command("list")
@click.option("--page", type=int, default=None)
@click.option("--page-size", type=int, default=None)
@click.option("--status", default=None, help="Filter by status.")
@click.pass_context
def tasks_list(ctx: click.Context, page: int | None, page_size: int | None, status: str | None) -> None:
    """List tasks."""
    params = {}
    if page is not None:
        params["page"] = page
    if page_size is not None:
        params["pageSize"] = page_size
    if status is not None:
        params["status"] = status
    client = build_client()
    result = client.request("GET", "/tasks", params=params or None)
    print_result(result, as_json=ctx.obj.get("json", False))


@tasks_group.command("get")
@click.argument("task_id")
@click.pass_context
def tasks_get(ctx: click.Context, task_id: str) -> None:
    """Get a task by ID."""
    client = build_client()
    result = client.request("GET", f"/tasks/{_q(task_id)}")
    print_result(result, as_json=ctx.obj.get("json", False))


@tasks_group.command("cancel")
@click.argument("task_id")
@click.option("--yes", "-y", is_flag=True)
@click.pass_context
def tasks_cancel(ctx: click.Context, task_id: str, yes: bool) -> None:
    """Cancel a running task."""
    confirm_action(
        f"Cancel task {task_id}?",
        yes=yes,
        non_interactive_error="Task cancel requires --yes for non-interactive use.",
    )
    client = build_client()
    result = client.request("POST", f"/tasks/{_q(task_id)}/cancel")
    print_result(result, as_json=ctx.obj.get("json", False))
