from __future__ import annotations

import click
import requests


class CLIError(click.ClickException):
    pass


def api_error(resp: requests.Response, operation: str) -> CLIError:
    try:
        body = resp.json()
        msg = body.get("message") or body.get("error") or str(resp.status_code)
    except Exception:
        msg = str(resp.status_code)
    return CLIError(f"{operation} failed ({resp.status_code}): {msg}")
