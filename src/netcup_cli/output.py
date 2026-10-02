from __future__ import annotations

import json

from rich.console import Console
from rich.table import Table
from rich import box

console = Console()


def print_result(value: object, *, as_json: bool = False) -> None:
    if as_json:
        print(json.dumps(value, indent=2, default=str))
        return
    if value is None:
        return
    if isinstance(value, list):
        if not value:
            console.print("[dim]No results.[/dim]")
            return
        if isinstance(value[0], dict):
            _print_table(value)
        else:
            for item in value:
                console.print(str(item))
    elif isinstance(value, dict):
        _print_dict(value)
    else:
        console.print(str(value))


def _print_table(rows: list[dict]) -> None:
    keys = list(rows[0].keys())
    t = Table(box=box.ROUNDED)
    for k in keys:
        t.add_column(str(k))
    for row in rows:
        t.add_row(*[str(row.get(k, "")) for k in keys])
    console.print(t)


def _print_dict(d: dict) -> None:
    t = Table(box=box.SIMPLE, show_header=False)
    t.add_column("Key", style="bold")
    t.add_column("Value")
    for k, v in d.items():
        t.add_row(str(k), json.dumps(v) if isinstance(v, (dict, list)) else str(v))
    console.print(t)
