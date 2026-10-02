from __future__ import annotations

import sys

import click

from netcup_cli.errors import CLIError


def confirm_action(message: str, *, yes: bool, non_interactive_error: str = "") -> None:
    if yes:
        return
    if not sys.stdin.isatty():
        raise CLIError(
            non_interactive_error
            or f"This operation requires confirmation. Re-run with --yes to proceed non-interactively."
        )
    click.confirm(message, abort=True)
