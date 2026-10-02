# netcup-cli

Command-line client for the [Netcup Server Control Panel (SCP) REST API](https://www.servercontrolpanel.de/).

## Installation

```bash
curl -fsSL https://raw.githubusercontent.com/Maxsander123/netcup-cli/main/scripts/install-netcup-cli.sh | bash
```

Requires [uv](https://astral.sh/uv) — if not installed yet:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Also installs the man page — read it with `man netcup-cli`.

## Quick start

```bash
netcup-cli login        # Browser-Login (no password needed)
netcup-cli list         # List all servers
netcup-cli info Mia     # Server details (nickname, hostname, or ID)
netcup-cli vnc Mia      # Open VNC console in browser
netcup-cli start Mia
netcup-cli stop Mia
netcup-cli reset Mia    # Hard reboot
```

## OS Images & Reinstall

```bash
# List available OS images (no server needed)
netcup-cli images

# List images for a specific server (architecture matters)
netcup-cli images Mia

# Interactive reinstall wizard
netcup-cli install Mia

# Non-interactive reinstall with all options
netcup-cli install Mia \
  --image 1234 \
  --hostname mia.example.com \
  --locale de_DE.UTF-8 \
  --timezone Europe/Berlin \
  --username admin \
  --ssh-key 456 \
  --no-ssh-password \
  --script ./post-install.sh \
  --yes
```

Install options match the SCP web UI:
`--image` · `--hostname` · `--locale` · `--timezone` · `--partitioning` ·
`--username` · `--password` · `--ssh-key` · `--no-ssh-password` · `--script` · `--send-email`

## SSH Keys

```bash
netcup-cli ssh-key list
netcup-cli ssh-key add mykey ~/.ssh/id_ed25519.pub
netcup-cli ssh-key add mykey --key "ssh-ed25519 AAAA..."
netcup-cli ssh-key delete <id>
```

## Snapshots

```bash
netcup-cli snapshot list Mia
netcup-cli snapshot create Mia --name vor-update
netcup-cli snapshot restore Mia <snap-id>   # confirms before overwriting
netcup-cli snapshot delete Mia <snap-id>
netcup-cli snapshot export Mia <snap-id>
```

## Reverse DNS

```bash
netcup-cli rdns ipv4 get 1.2.3.4
netcup-cli rdns ipv4 set 1.2.3.4 --hostname mail.example.com
netcup-cli rdns ipv4 delete 1.2.3.4
netcup-cli rdns ipv6 get 2a06::1
```

## Tasks

```bash
netcup-cli tasks list
netcup-cli tasks get <id>
netcup-cli tasks cancel <id>
```

## JSON output

```bash
netcup-cli --json list | jq '.[].id'
netcup-cli --json info Mia | jq '.serverLiveInfo.interfaces'
```

## Automation (non-interactive)

All destructive commands require `--yes` / `-y` when stdin is not a terminal:

```bash
netcup-cli stop Mia --yes
netcup-cli snapshot delete Mia <id> --yes
netcup-cli install Mia --image 1234 --yes
```

## All commands

| Command | Description |
|---------|-------------|
| `login` | Browser device-code login |
| `logout` | Remove local credentials |
| `whoami` | Show login status |
| `list` | List all servers |
| `info <server>` | Server details incl. all interfaces |
| `start/stop/reset <server>` | Power management |
| `vnc <server>` | Open SCP web console in browser |
| `images [server]` | List available OS images |
| `install <server>` | Reinstall / install new OS (wizard) |
| `snapshot` | Manage snapshots |
| `ssh-key` | Manage SSH public keys |
| `rdns` | Manage reverse DNS |
| `tasks` | Manage async tasks |
| `users` | User account, failover IPs, firewall policies |
| `servers` | Advanced: disks, interfaces, metrics, ISO |
| `completion bash\|zsh\|fish` | Shell completion |

Full documentation: `man netcup-cli`
