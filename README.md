# netcup-cli

Command-line client for the [Netcup Server Control Panel (SCP) REST API](https://www.servercontrolpanel.de/).

## Requirements

- Python 3.10 or newer
- Internet access to `servercontrolpanel.de`

## Installation

```bash
bash scripts/install-netcup-cli.sh
```

Or install into any Python environment:

```bash
pip install -e .
```

From source (GitHub):

```bash
git clone https://github.com/Maxsander123/netcup-cli
cd netcup-cli
pip install -e .
```

## Authentication

netcup-cli uses the Netcup OIDC device-code flow. No password is required.

```bash
netcup-cli auth login
# Opens a browser URL — authenticate there, then return to the terminal.
```

Credentials (refresh token only) are stored in `~/.config/netcup-cli/credentials.json` (mode 0600).

```bash
netcup-cli auth show    # Check login status
netcup-cli auth logout  # Remove local credentials
netcup-cli auth revoke  # Revoke token with provider and remove local credentials
```

## Quick start

```bash
# List servers
netcup-cli servers list

# Get server details
netcup-cli servers get 12345

# Change power state (prompts for confirmation)
netcup-cli servers power 12345 stop

# Skip confirmation for automation
netcup-cli servers power 12345 stop --yes

# JSON output for scripting
netcup-cli --json servers list | jq '.[].hostname'

# Reverse DNS
netcup-cli rdns ipv4 set 1.2.3.4 --hostname mail.example.com
netcup-cli rdns ipv6 get 2a06::1

# Snapshots
netcup-cli servers snapshots create 12345 --name before-upgrade
netcup-cli servers snapshots list 12345
netcup-cli servers snapshots revert 12345 snap-id --yes
```

## Command groups

| Group | Description |
|-------|-------------|
| `auth` | Login, logout, revoke, show |
| `api` | Ping, OpenAPI schema |
| `maintenance` | Maintenance info (deprecated) |
| `rdns` | IPv4/IPv6 reverse DNS |
| `servers` | Server management, power, disks, images, ISOs, interfaces, metrics, rescue, snapshots |
| `tasks` | List, get, cancel async tasks |
| `users` | User details, SSH keys, failover IPs, firewall policies, images, ISOs, VLANs |
| `vlans` | VLAN lookup |

See [docs/commands.md](docs/commands.md) for the full command reference.

## JSON output

Add `--json` before any command to get machine-readable output:

```bash
netcup-cli --json servers list
netcup-cli --json tasks list --status running
```

## Automation (non-interactive)

Destructive commands require `--yes` when stdin is not a terminal:

```bash
netcup-cli servers power 12345 stop --yes
netcup-cli servers disks format 12345 disk-id --filesystem ext4 --yes
```

## Links

- [Installation](docs/installation.md)
- [Authentication](docs/authentication.md)
- [Configuration](docs/configuration.md)
- [Command reference](docs/commands.md)
- [API coverage](docs/api-coverage.md)
- [Troubleshooting](docs/troubleshooting.md)
- [Source](https://github.com/Maxsander123/netcup-cli)
