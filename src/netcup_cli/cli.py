from __future__ import annotations

import click

from netcup_cli import __version__
from netcup_cli.commands.auth import auth_group
from netcup_cli.commands.disks import disks_group
from netcup_cli.commands.images import (
    server_image_group,
    server_iso_group,
    server_snapshots_group,
)
from netcup_cli.commands.metrics import metrics_group
from netcup_cli.commands.misc import api_group, maintenance_group
from netcup_cli.commands.networking import (
    rdns_group,
    server_interfaces_group,
    vlans_group,
)
from netcup_cli.commands.servers import servers_group
from netcup_cli.commands.tasks import tasks_group
from netcup_cli.commands.users import users_group


@click.group()
@click.version_option(__version__, prog_name="netcup-cli")
@click.option("--json", "as_json", is_flag=True, default=False, help="Output raw JSON.")
@click.pass_context
def cli(ctx: click.Context, as_json: bool) -> None:
    """netcup-cli — Command-line client for the Netcup Server Control Panel API."""
    ctx.ensure_object(dict)
    ctx.obj["json"] = as_json


cli.add_command(auth_group)
cli.add_command(api_group)
cli.add_command(maintenance_group)
cli.add_command(rdns_group)
cli.add_command(tasks_group)
cli.add_command(users_group)
cli.add_command(vlans_group)

# servers and its subgroups
servers_group.add_command(disks_group)
servers_group.add_command(server_image_group, name="image")
servers_group.add_command(server_iso_group, name="iso")
servers_group.add_command(server_interfaces_group, name="interfaces")
servers_group.add_command(metrics_group)
servers_group.add_command(server_snapshots_group, name="snapshots")
cli.add_command(servers_group)


@cli.command("completion")
@click.argument("shell", type=click.Choice(["bash", "zsh", "fish"]))
def completion(shell: str) -> None:
    """Print shell completion script.

    Add to your shell config:
      bash: eval "$(netcup-cli completion bash)"
      zsh:  eval "$(netcup-cli completion zsh)"
      fish: netcup-cli completion fish | source
    """
    import os
    env_var = f"_NETCUP_CLI_COMPLETE={shell}_source"
    os.environ[env_var.split("=")[0]] = env_var.split("=")[1]
    from netcup_cli.cli import cli as _cli
    import subprocess
    result = subprocess.run(
        ["python", "-m", "netcup_cli"],
        env={**os.environ, f"_NETCUP_CLI_COMPLETE": f"{shell}_source"},
        capture_output=True,
        text=True,
    )
    click.echo(result.stdout, nl=False)
