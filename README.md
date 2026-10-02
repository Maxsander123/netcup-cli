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

## Update

```bash
netcup-cli update
```

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
netcup-cli snapshot check Mia                  # dry-run: is a snapshot possible?
netcup-cli snapshot list Mia
netcup-cli snapshot create Mia --name vor-update
netcup-cli snapshot create Mia --name x --disk vda   # offline, single disk (required on UEFI servers)
netcup-cli snapshot restore Mia <name>         # confirms before overwriting
netcup-cli snapshot delete Mia <name>
netcup-cli snapshot export Mia <name>
```

Snapshots are identified by **name**, not by a numeric ID.

## Advanced server operations

```bash
netcup-cli servers update Mia --nickname Foo --autostart --bootorder HDD,CDROM
netcup-cli servers power Mia reset             # on | off | poweroff | reset | powercycle | suspend
netcup-cli servers rescue activate Mia         # server must be off; password shown via 'rescue status'
netcup-cli servers rescue deactivate Mia
netcup-cli servers iso list Mia                # netcup-provided ISOs
netcup-cli servers iso attach Mia --iso-id 80  # or --user-iso <name>
netcup-cli servers iso detach Mia
netcup-cli servers disks list Mia
netcup-cli servers metrics cpu|disk|network|packets Mia --hours 6 --last 20
netcup-cli servers logs Mia --limit 10
netcup-cli servers user-image Mia <image-name> # install an uploaded image
```

Everywhere a server is expected you can pass its numeric ID, nickname, hostname or
the internal name (`v2202…`).

## Async tasks

Actions like start/stop/snapshot/ISO/rescue are asynchronous. By default the CLI waits and
shows progress until the task finishes. Use `--no-wait` to return immediately:

```bash
netcup-cli --no-wait stop Mia
netcup-cli tasks list --limit 5 --state RUNNING
netcup-cli tasks get <uuid>
```

## Reverse DNS

```bash
netcup-cli rdns ipv4 get 1.2.3.4
netcup-cli rdns ipv4 set 1.2.3.4 --hostname mail.example.com   # must be a valid FQDN
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
| `update` | Update to latest version from GitHub |
| `completion bash\|zsh\|fish` | Shell completion |

Full documentation: `man netcup-cli`
