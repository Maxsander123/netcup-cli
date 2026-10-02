from __future__ import annotations

from urllib.parse import quote

import click

from netcup_cli.client import build_client
from rich import box
from rich.table import Table

from netcup_cli.output import console, print_result
from netcup_cli.safety import confirm_action


def _q(s: str) -> str:
    return quote(str(s), safe="")


@click.group("tasks")
def tasks_group() -> None:
    """Manage asynchronous tasks."""


@tasks_group.command("list")
@click.option("--limit", type=int, default=20, show_default=True)
@click.option("--offset", type=int, default=0, show_default=True)
@click.option("--server", "server_id", type=int, default=None, help="Filter by server ID.")
@click.option("--state", default=None, help="Filter by state, e.g. RUNNING, FINISHED, ERROR.")
@click.pass_context
def tasks_list(ctx: click.Context, limit: int, offset: int, server_id: int | None, state: str | None) -> None:
    """List tasks (newest first)."""
    params: dict = {"limit": limit, "offset": offset}
    if server_id is not None:
        params["serverId"] = server_id
    if state is not None:
        params["state"] = state
    client = build_client()
    result = client.request("GET", "/tasks", params=params)
    if ctx.obj.get("json") or not isinstance(result, list) or not result:
        print_result(result, as_json=ctx.obj.get("json", False))
        return
    t = Table(box=box.ROUNDED)
    t.add_column("UUID", style="cyan", no_wrap=True)
    t.add_column("Task", style="bold")
    t.add_column("State")
    t.add_column("Progress", justify="right")
    t.add_column("Started")
    t.add_column("Message", overflow="fold")
    for task in result:
        st = task.get("state") or "—"
        colour = {"FINISHED": "green", "ERROR": "red", "RUNNING": "yellow"}.get(st, "white")
        pct = (task.get("taskProgress") or {}).get("progressInPercent")
        t.add_row(
            task.get("uuid") or "—",
            (task.get("name") or "—").removesuffix("Task"),
            f"[{colour}]{st}[/{colour}]",
            f"{pct:.0f}%" if isinstance(pct, (int, float)) else "—",
            (task.get("startedAt") or "")[:19].replace("T", " ") or "—",
            task.get("message") or "",
        )
    console.print(t)


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
    result = client.request("PUT", f"/tasks/{_q(task_id)}:cancel")
    print_result(result, as_json=ctx.obj.get("json", False))
