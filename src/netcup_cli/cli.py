from __future__ import annotations

from urllib.parse import quote

import click

from netcup_cli import __version__
from netcup_cli.auth import AuthClient
from netcup_cli.client import SCPClient, build_client
from netcup_cli.config import Credentials, delete_credentials, load_credentials, save_credentials
from netcup_cli.errors import CLIError
from netcup_cli.output import console, print_result, print_server, print_servers

import shutil
import subprocess as _subprocess
from netcup_cli.safety import confirm_action

# Advanced subgroups
from netcup_cli.commands.disks import disks_group
from netcup_cli.commands.images import server_iso_group, server_snapshots_group
from netcup_cli.commands.metrics import metrics_group
from netcup_cli.commands.misc import api_group, maintenance_group
from netcup_cli.commands.networking import rdns_group, server_interfaces_group, vlans_group
from netcup_cli.commands.tasks import tasks_group
from netcup_cli.commands.users import users_group


def _q(s: str) -> str:
    return quote(str(s), safe="")


def _resolve(client: SCPClient, name: str) -> str:
    """Resolve nickname, hostname, or numeric ID to a server ID string."""
    if str(name).isdigit():
        return str(name)
    servers = client.request("GET", "/servers")
    items: list[dict] = servers if isinstance(servers, list) else (servers or {}).get("data", [])  # type: ignore[union-attr]
    for s in items:
        if s.get("nickname") == name or s.get("hostname") == name or str(s.get("id")) == name:
            return str(s["id"])
    raise CLIError(f"No server found for '{name}'. Use 'netcup-cli list' to see available servers.")


@click.group()
@click.version_option(__version__, prog_name="netcup-cli")
@click.option("--json", "as_json", is_flag=True, default=False, help="Output raw JSON.")
@click.pass_context
def cli(ctx: click.Context, as_json: bool) -> None:
    """netcup-cli — Netcup Server Control Panel CLI."""
    ctx.ensure_object(dict)
    ctx.obj["json"] = as_json


# ── auth ──────────────────────────────────────────────────────────────────────

@cli.command("login")
def cmd_login() -> None:
    """Login via browser (device code — no password needed)."""
    client = AuthClient()
    token_set = client.login_device()
    save_credentials(Credentials(refresh_token=token_set.refresh_token))  # type: ignore[arg-type]
    console.print("[green]✓[/green] Logged in.")


@cli.command("logout")
def cmd_logout() -> None:
    """Remove locally saved credentials."""
    delete_credentials()
    console.print("[green]✓[/green] Logged out.")


@cli.command("whoami")
def cmd_whoami() -> None:
    """Show login status."""
    creds = load_credentials()
    if creds is None:
        console.print("[yellow]Not logged in.[/yellow]  Run: netcup-cli login")
    else:
        console.print("[green]Logged in.[/green]  Refresh token stored locally.")


# ── server list / info ────────────────────────────────────────────────────────

@cli.command("list")
@click.pass_context
def cmd_list(ctx: click.Context) -> None:
    """List all servers."""
    client = build_client()
    result = client.request("GET", "/servers")
    servers: list[dict] = result if isinstance(result, list) else (result or {}).get("data", [])  # type: ignore[union-attr]
    print_servers(servers, as_json=ctx.obj.get("json", False))


@cli.command("info")
@click.argument("server")
@click.pass_context
def cmd_info(ctx: click.Context, server: str) -> None:
    """Show details for a server (ID, nickname, or hostname)."""
    client = build_client()
    server_id = _resolve(client, server)
    result = client.request("GET", f"/servers/{_q(server_id)}")
    print_server(result, as_json=ctx.obj.get("json", False))  # type: ignore[arg-type]


# `get` as alias for `info`
@cli.command("get", hidden=True)
@click.argument("server")
@click.pass_context
def cmd_get(ctx: click.Context, server: str) -> None:
    """Alias for 'info'."""
    ctx.invoke(cmd_info, server=server)


# ── power commands ────────────────────────────────────────────────────────────

@cli.command("start")
@click.argument("server")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.pass_context
def cmd_start(ctx: click.Context, server: str, yes: bool) -> None:
    """Start a server."""
    client = build_client()
    server_id = _resolve(client, server)
    confirm_action(f"Start server {server} ({server_id})?", yes=yes)
    result = client.request("POST", f"/servers/{_q(server_id)}/power", json_body={"action": "START"})
    print_result(result, as_json=ctx.obj.get("json", False))


@cli.command("stop")
@click.argument("server")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.pass_context
def cmd_stop(ctx: click.Context, server: str, yes: bool) -> None:
    """Gracefully stop a server."""
    client = build_client()
    server_id = _resolve(client, server)
    confirm_action(f"Stop server {server} ({server_id})?", yes=yes)
    result = client.request("POST", f"/servers/{_q(server_id)}/power", json_body={"action": "STOP"})
    print_result(result, as_json=ctx.obj.get("json", False))


@cli.command("reset")
@click.argument("server")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.pass_context
def cmd_reset(ctx: click.Context, server: str, yes: bool) -> None:
    """Hard-reset (reboot) a server."""
    client = build_client()
    server_id = _resolve(client, server)
    confirm_action(f"Hard-reset server {server} ({server_id})? This interrupts the server.", yes=yes)
    result = client.request("POST", f"/servers/{_q(server_id)}/power", json_body={"action": "HARD_REBOOT"})
    print_result(result, as_json=ctx.obj.get("json", False))


# ── vnc ───────────────────────────────────────────────────────────────────────

_VNC_BASE = "https://www.servercontrolpanel.de/scp-ui/servers"


def _open_browser(url: str) -> None:
    for opener in ("xdg-open", "sensible-browser", "x-www-browser", "firefox", "chromium-browser", "google-chrome"):
        if shutil.which(opener):
            _subprocess.Popen([opener, url], stdout=_subprocess.DEVNULL, stderr=_subprocess.DEVNULL)
            return
    console.print(f"[yellow]No browser found. Open manually:[/yellow]\n  {url}")


@cli.command("vnc")
@click.argument("server")
@click.option("--url-only", is_flag=True, help="Print the URL instead of opening the browser.")
@click.pass_context
def cmd_vnc(ctx: click.Context, server: str, url_only: bool) -> None:
    """Open the VNC/serial console for a server in the browser."""
    client = build_client()
    server_id = _resolve(client, server)
    url = f"{_VNC_BASE}/{server_id}/screen"
    if url_only:
        click.echo(url)
        return
    console.print(f"Opening VNC console for [bold]{server}[/bold] ({server_id}) ...")
    console.print(f"[dim]{url}[/dim]")
    console.print("[dim]Log in to servercontrolpanel.de in the browser if prompted.[/dim]")
    _open_browser(url)


# ── snapshot subgroup ─────────────────────────────────────────────────────────

@cli.group("snapshot")
def snapshot_group() -> None:
    """Manage server snapshots."""


@snapshot_group.command("list")
@click.argument("server")
@click.pass_context
def snapshot_list(ctx: click.Context, server: str) -> None:
    """List snapshots for a server."""
    client = build_client()
    server_id = _resolve(client, server)
    result = client.request("GET", f"/servers/{_q(server_id)}/snapshots")
    print_result(result, as_json=ctx.obj.get("json", False))


@snapshot_group.command("create")
@click.argument("server")
@click.option("--name", "-n", required=True, help="Snapshot name.")
@click.option("--description", "-d", default="", help="Optional description.")
@click.pass_context
def snapshot_create(ctx: click.Context, server: str, name: str, description: str) -> None:
    """Create a snapshot."""
    client = build_client()
    server_id = _resolve(client, server)
    body: dict = {"name": name}
    if description:
        body["description"] = description
    result = client.request("POST", f"/servers/{_q(server_id)}/snapshots", json_body=body)
    print_result(result, as_json=ctx.obj.get("json", False))


@snapshot_group.command("delete")
@click.argument("server")
@click.argument("snapshot_id")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.pass_context
def snapshot_delete(ctx: click.Context, server: str, snapshot_id: str, yes: bool) -> None:
    """Delete a snapshot. Cannot be undone."""
    client = build_client()
    server_id = _resolve(client, server)
    confirm_action(f"Delete snapshot {snapshot_id} from {server}? Cannot be undone.", yes=yes)
    result = client.request("DELETE", f"/servers/{_q(server_id)}/snapshots/{_q(snapshot_id)}")
    print_result(result, as_json=ctx.obj.get("json", False))


@snapshot_group.command("restore")
@click.argument("server")
@click.argument("snapshot_id")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.pass_context
def snapshot_restore(ctx: click.Context, server: str, snapshot_id: str, yes: bool) -> None:
    """Restore a server from a snapshot. All current disk data will be lost."""
    client = build_client()
    server_id = _resolve(client, server)
    confirm_action(
        f"Restore snapshot {snapshot_id} onto {server}? All current disk data will be lost.",
        yes=yes,
    )
    result = client.request("POST", f"/servers/{_q(server_id)}/snapshots/{_q(snapshot_id)}/revert")
    print_result(result, as_json=ctx.obj.get("json", False))


@snapshot_group.command("export")
@click.argument("server")
@click.argument("snapshot_id")
@click.pass_context
def snapshot_export(ctx: click.Context, server: str, snapshot_id: str) -> None:
    """Export a snapshot."""
    client = build_client()
    server_id = _resolve(client, server)
    result = client.request("POST", f"/servers/{_q(server_id)}/snapshots/{_q(snapshot_id)}/export")
    print_result(result, as_json=ctx.obj.get("json", False))


# ── images (list available OS images) ────────────────────────────────────────

@cli.command("images")
@click.argument("server", required=False, default=None)
@click.option("--all", "show_deprecated", is_flag=True, help="Include deprecated images.")
@click.pass_context
def cmd_images(ctx: click.Context, server: str | None, show_deprecated: bool) -> None:
    """List available OS images.

    Without SERVER uses the first server on your account to fetch the image catalogue.
    Images are architecture-specific — pass a different SERVER to see its available images.
    """
    from rich.table import Table
    from rich import box as rbox
    import json as _json
    client = build_client()

    if server:
        server_id = _resolve(client, server)
        label = server
    else:
        all_servers = client.request("GET", "/servers")
        items_s: list[dict] = all_servers if isinstance(all_servers, list) else (all_servers or {}).get("data", [])  # type: ignore[union-attr]
        if not items_s:
            raise CLIError("No servers found on your account.")
        server_id = str(items_s[0]["id"])
        label = items_s[0].get("nickname") or items_s[0].get("hostname") or server_id

    # Try known paths — the actual path depends on the SCP API version
    result = None
    last_err: Exception | None = None
    for candidate in (
        f"/servers/{_q(server_id)}/image/flavours",
        f"/servers/{_q(server_id)}/images/flavours",
        f"/servers/{_q(server_id)}/images",
    ):
        try:
            result = client.request("GET", candidate)
            break
        except CLIError as exc:
            last_err = exc
    if result is None:
        raise CLIError(
            f"Could not fetch images ({last_err}).\n"
            f"Tip: browse https://www.servercontrolpanel.de/scp-ui/servers/{server_id}/media/images"
        )
    if ctx.obj.get("json"):
        click.echo(_json.dumps(result, indent=2, default=str))
        return
    items: list[dict] = result if isinstance(result, list) else (result or {}).get("data", [])  # type: ignore[union-attr]
    if not show_deprecated:
        items = [i for i in items if not i.get("deprecated")]
    if not items:
        console.print("[dim]No images available.[/dim]")
        return
    t = Table(box=rbox.ROUNDED, title=f"OS Images — {label}")
    t.add_column("ID", style="cyan", no_wrap=True)
    t.add_column("Name", style="bold")
    t.add_column("Method")
    t.add_column("Arch")
    if show_deprecated:
        t.add_column("Deprecated", style="dim")
    for img in items:
        row = [
            str(img.get("id", "")),
            img.get("name") or "—",
            img.get("installationMethod") or "—",
            img.get("architecture") or "—",
        ]
        if show_deprecated:
            row.append("yes" if img.get("deprecated") else "")
        t.add_row(*row)
    console.print(t)
    console.print(f"[dim]{len(items)} image(s)[/dim]")


# ── install (reinstall / new OS) ──────────────────────────────────────────────

@cli.command("install")
@click.argument("server")
@click.option("--image", "image_id", default=None, help="Image ID (from 'netcup-cli images <server>').")
@click.option("--hostname", default=None, help="Hostname to set after install.")
@click.option("--locale", default=None, help="Locale, e.g. de_DE.UTF-8")
@click.option("--timezone", default=None, help="Timezone, e.g. Europe/Berlin")
@click.option("--partitioning", default=None, help="Partitioning scheme ID (leave blank for default).")
@click.option("--username", default=None, help="Additional user to create.")
@click.option("--password", default=None, help="Password for the additional user (prompted if omitted).")
@click.option("--ssh-key", "ssh_key_ids", multiple=True, help="SSH key ID to inject (repeatable). Use 'netcup-cli ssh-key list'.")
@click.option("--no-ssh-password", is_flag=True, default=False, help="Disable SSH password authentication.")
@click.option("--script", "script_file", type=click.Path(exists=True), default=None, help="Custom post-install script file.")
@click.option("--send-email", is_flag=True, default=False, help="Send confirmation e-mail after install.")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.pass_context
def cmd_install(
    ctx: click.Context,
    server: str,
    image_id: str | None,
    hostname: str | None,
    locale: str | None,
    timezone: str | None,
    partitioning: str | None,
    username: str | None,
    password: str | None,
    ssh_key_ids: tuple[str, ...],
    no_ssh_password: bool,
    script_file: str | None,
    send_email: bool,
    yes: bool,
) -> None:
    """Reinstall or install a new OS on a server.

    Lists available images with: netcup-cli images <server>
    Lists SSH keys with:         netcup-cli ssh-key list
    """
    from rich.table import Table
    from rich import box as rbox
    import getpass as _getpass

    client = build_client()
    server_id = _resolve(client, server)

    # ── Interactive image picker if --image not given ─────────────────────────
    if not image_id:
        result = client.request("GET", f"/servers/{_q(server_id)}/image/flavours")
        items: list[dict] = result if isinstance(result, list) else (result or {}).get("data", [])  # type: ignore[union-attr]
        items = [i for i in items if not i.get("deprecated")]
        if not items:
            raise CLIError("No images available for this server.")
        t = Table(box=rbox.ROUNDED, title=f"Available OS Images — {server}")
        t.add_column("#", style="dim")
        t.add_column("ID", style="cyan", no_wrap=True)
        t.add_column("Name", style="bold")
        t.add_column("Method")
        for idx, img in enumerate(items, 1):
            t.add_row(str(idx), str(img.get("id", "")), img.get("name") or "—", img.get("installationMethod") or "—")
        console.print(t)
        raw = click.prompt("Select image number")
        if not raw.isdigit() or not (1 <= int(raw) <= len(items)):
            raise CLIError("Invalid selection.")
        chosen = items[int(raw) - 1]
        image_id = str(chosen["id"])
        console.print(f"Selected: [bold]{chosen.get('name')}[/bold] (ID {image_id})")

    # ── Prompt for missing common options ─────────────────────────────────────
    if not hostname:
        hostname = click.prompt("Hostname", default=server)
    if not locale:
        locale = click.prompt("Locale", default="en_US.UTF-8")
    if not timezone:
        timezone = click.prompt("Timezone", default="Europe/Berlin")

    # ── Optional user creation ────────────────────────────────────────────────
    if not username:
        create_user = click.confirm("Create additional user?", default=False)
        if create_user:
            username = click.prompt("Username")

    if username and not password:
        password = _getpass.getpass(f"Password for '{username}': ")

    # ── SSH key picker if none given ──────────────────────────────────────────
    if not ssh_key_ids:
        keys_result = client.request("GET", "/users/me/ssh-keys")
        keys: list[dict] = keys_result if isinstance(keys_result, list) else (keys_result or {}).get("data", [])  # type: ignore[union-attr]
        if keys:
            console.print("\nAvailable SSH keys:")
            for k in keys:
                console.print(f"  [cyan]{k.get('id')}[/cyan]  {k.get('name')}")
            raw_keys = click.prompt("SSH key IDs to inject (comma-separated, or leave blank)", default="")
            if raw_keys.strip():
                ssh_key_ids = tuple(k.strip() for k in raw_keys.split(",") if k.strip())

    # ── Custom script ─────────────────────────────────────────────────────────
    script_content: str | None = None
    if script_file:
        script_content = open(script_file).read()
        if len(script_content) > 10000:
            raise CLIError("Custom script exceeds 10,000 character limit.")

    # ── Build request body ────────────────────────────────────────────────────
    body: dict = {"imageId": image_id}
    if hostname:
        body["hostname"] = hostname
    if locale:
        body["locale"] = locale
    if timezone:
        body["timezone"] = timezone
    if partitioning:
        body["partitioning"] = partitioning
    if username:
        body["createAdditionalUser"] = True
        body["username"] = username
    if password:
        body["userPassword"] = password
    if ssh_key_ids:
        body["sshKeyIds"] = list(ssh_key_ids)
    body["sshPasswordAuthentication"] = not no_ssh_password
    if script_content:
        body["customScript"] = script_content
    body["sendEmail"] = send_email

    # ── Summary + confirmation ────────────────────────────────────────────────
    console.print(f"\n[bold yellow]Install summary for {server} ({server_id}):[/bold yellow]")
    console.print(f"  Image:    {image_id}")
    console.print(f"  Hostname: {hostname}")
    console.print(f"  Locale:   {locale}  /  Timezone: {timezone}")
    if username:
        console.print(f"  User:     {username}")
    if ssh_key_ids:
        console.print(f"  SSH keys: {', '.join(ssh_key_ids)}")
    console.print(f"  SSH password auth: {'disabled' if no_ssh_password else 'enabled'}")
    if script_content:
        console.print(f"  Custom script: {len(script_content)} chars")

    confirm_action(
        f"\nInstall image on {server}? The disk will be FORMATTED — all data will be lost.",
        yes=yes,
    )

    result = client.request("POST", f"/servers/{_q(server_id)}/image/install", json_body=body)
    print_result(result, as_json=ctx.obj.get("json", False))
    console.print("[green]✓[/green] Install started.")


# ── ssh-key management ────────────────────────────────────────────────────────

@cli.group("ssh-key")
def ssh_key_group() -> None:
    """Manage SSH public keys on your account."""


@ssh_key_group.command("list")
@click.pass_context
def ssh_key_list(ctx: click.Context) -> None:
    """List all SSH keys on your account."""
    from rich.table import Table
    from rich import box as rbox
    client = build_client()
    result = client.request("GET", "/users/me/ssh-keys")
    if ctx.obj.get("json"):
        import json
        click.echo(json.dumps(result, indent=2, default=str))
        return
    keys: list[dict] = result if isinstance(result, list) else (result or {}).get("data", [])  # type: ignore[union-attr]
    if not keys:
        console.print("[dim]No SSH keys on your account.[/dim]")
        return
    t = Table(box=rbox.ROUNDED)
    t.add_column("ID", style="cyan", no_wrap=True)
    t.add_column("Name", style="bold")
    t.add_column("Fingerprint")
    for k in keys:
        t.add_row(str(k.get("id", "")), k.get("name") or "—", k.get("fingerprint") or k.get("publicKey", "")[:40] + "…")
    console.print(t)


@ssh_key_group.command("add")
@click.argument("name")
@click.argument("pubkey_file", type=click.Path(exists=True), required=False)
@click.option("--key", "key_str", default=None, help="Public key string (alternative to file).")
@click.pass_context
def ssh_key_add(ctx: click.Context, name: str, pubkey_file: str | None, key_str: str | None) -> None:
    """Upload an SSH public key.

    \b
    Examples:
      netcup-cli ssh-key add mykey ~/.ssh/id_ed25519.pub
      netcup-cli ssh-key add mykey --key "ssh-ed25519 AAAA..."
    """
    if pubkey_file:
        pub = open(pubkey_file).read().strip()
    elif key_str:
        pub = key_str.strip()
    else:
        pub = click.prompt("Public key").strip()
    client = build_client()
    result = client.request("POST", "/users/me/ssh-keys", json_body={"name": name, "publicKey": pub})
    print_result(result, as_json=ctx.obj.get("json", False))
    console.print(f"[green]✓[/green] SSH key '{name}' added.")


@ssh_key_group.command("delete")
@click.argument("key_id")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.pass_context
def ssh_key_delete(ctx: click.Context, key_id: str, yes: bool) -> None:
    """Delete an SSH key. May remove server access."""
    confirm_action(
        f"Delete SSH key {key_id}? This may remove access to servers using this key.",
        yes=yes,
    )
    client = build_client()
    client.request("DELETE", f"/users/me/ssh-keys/{_q(key_id)}")
    console.print(f"[green]✓[/green] SSH key {key_id} deleted.")


# ── advanced subgroups ────────────────────────────────────────────────────────

cli.add_command(rdns_group)
cli.add_command(tasks_group)
cli.add_command(users_group)
cli.add_command(vlans_group)
cli.add_command(api_group)
cli.add_command(maintenance_group)

from netcup_cli.commands.servers import servers_group
servers_group.add_command(disks_group)
servers_group.add_command(server_iso_group, name="iso")
servers_group.add_command(server_interfaces_group, name="interfaces")
servers_group.add_command(metrics_group)
servers_group.add_command(server_snapshots_group, name="snapshots")
cli.add_command(servers_group)


@cli.command("completion")
@click.argument("shell", type=click.Choice(["bash", "zsh", "fish"]))
def completion(shell: str) -> None:
    """Print shell completion script."""
    import os
    import subprocess
    result = subprocess.run(
        ["python3", "-m", "netcup_cli"],
        env={**os.environ, "_NETCUP_CLI_COMPLETE": f"{shell}_source"},
        capture_output=True,
        text=True,
    )
    click.echo(result.stdout, nl=False)
