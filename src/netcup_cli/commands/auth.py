from __future__ import annotations

import click

from netcup_cli.auth import AuthClient
from netcup_cli.config import (
    Credentials,
    delete_credentials,
    load_credentials,
    save_credentials,
)
from netcup_cli.errors import CLIError
from netcup_cli.output import console


@click.group("auth")
def auth_group() -> None:
    """Manage authentication credentials."""


@auth_group.command("login")
def auth_login() -> None:
    """Login to Netcup SCP via browser (device code flow — no password needed)."""
    client = AuthClient()
    token_set = client.login_device()
    save_credentials(Credentials(refresh_token=token_set.refresh_token))  # type: ignore[arg-type]
    console.print("[green]✓[/green] Logged in successfully.")


@auth_group.command("logout")
def auth_logout() -> None:
    """Remove locally saved credentials (does not revoke the token)."""
    delete_credentials()
    console.print("[green]✓[/green] Logged out.")


@auth_group.command("revoke")
def auth_revoke() -> None:
    """Revoke the refresh token with the OIDC provider and remove local credentials."""
    creds = load_credentials()
    if creds is None:
        raise CLIError("Not logged in.")
    client = AuthClient()
    client.revoke(creds.refresh_token)
    delete_credentials()
    console.print("[green]✓[/green] Token revoked and credentials removed.")


@auth_group.command("show")
def auth_show() -> None:
    """Show whether credentials are stored locally."""
    creds = load_credentials()
    if creds is None:
        console.print("[yellow]Not logged in.[/yellow] Run 'netcup-cli auth login' to authenticate.")
    else:
        console.print("[green]Logged in.[/green] A refresh token is stored locally.")
