from __future__ import annotations

import click
import requests


class CLIError(click.ClickException):
    pass


def api_error(resp: requests.Response, operation: str) -> CLIError:
    try:
        body = resp.json()
    except Exception:
        body = None
    if isinstance(body, list):
        msg = "; ".join(str(e.get("message") or e.get("code") or e) if isinstance(e, dict) else str(e) for e in body)
    elif isinstance(body, dict):
        msg = body.get("message") or body.get("error") or str(body)
    else:
        msg = resp.text.strip()[:300] or resp.reason
    return CLIError(f"{operation} failed ({resp.status_code}): {msg}")
