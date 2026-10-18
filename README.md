# netcup-cli

Command-line client for the [Netcup Server Control Panel (SCP) REST API](https://www.servercontrolpanel.de/) and Customer Control Panel DNS APIs.

## Installation

Requires [uv](https://docs.astral.sh/uv/). Install it first if needed:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Then install the latest version from GitHub:

```bash
curl -fsSL https://raw.githubusercontent.com/Maxsander123/netcup-cli/main/scripts/install-netcup-cli.sh | bash
```

The installer installs the CLI and man page. If the shell cannot find
`netcup-cli`, add `~/.local/bin` to `PATH` and open a new shell. Check it with
`netcup-cli --version`. See [Installation](docs/installation.md) for source and
development installs.

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

`login` opens a browser-based sign-in and saves the SCP refresh token locally.
Check status with `netcup-cli whoami`; `netcup-cli logout` removes the local
token. SCP login is for server and SCP API commands.

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

## More server operations

```bash
netcup-cli set Mia --nickname Foo --autostart --bootorder HDD,CDROM
netcup-cli power Mia reset             # on | off | poweroff | reset | powercycle | suspend
netcup-cli rescue activate Mia         # server must be off; password shown via 'rescue status'
netcup-cli rescue deactivate Mia
netcup-cli iso list Mia                # netcup-provided ISOs
netcup-cli iso attach Mia --iso-id 80  # or --user-iso <name>
netcup-cli iso detach Mia
netcup-cli disks list Mia
netcup-cli metrics cpu Mia --hours 6 --last 20
netcup-cli metrics disk Mia --hours 6 --last 20
netcup-cli metrics network Mia --hours 6 --last 20
netcup-cli metrics packets Mia --hours 6 --last 20
netcup-cli logs Mia --limit 10
netcup-cli user-image Mia <image-name> # install an uploaded image
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

## Domain DNS (CCP)

CCP DNS uses separate credentials from SCP login. Choose the setup command for
the DNS API and commands you plan to use:

```bash
netcup-cli dns auth set legacy # classic zone and records
netcup-cli dns auth set rest   # CloudDNS domains, ACME, changesets, revisions
netcup-cli dns auth set ddns   # CloudDNS Dynamic DNS updates
netcup-cli dns auth show       # status only; never prints secrets
```

Legacy setup asks for your CCP customer number, Legacy API key, and Legacy API
password. REST setup asks for a CloudDNS REST API key; Dynamic DNS asks for its
token. Prompts hide secret input and save it in a separate
`ccp-credentials.json` file with mode `0600`. `dns auth clear
legacy|rest|ddns|all` removes saved CCP credentials; `netcup-cli logout` only
removes the SCP login.

For scripts, provide the relevant variables instead of saving secrets:
`NETCUP_CCP_CUSTOMER_NUMBER`, `NETCUP_CCP_LEGACY_API_KEY`,
`NETCUP_CCP_LEGACY_API_PASSWORD`, `NETCUP_API_KEY`, or `NETCUP_DDNS_TOKEN`.
Environment values override saved CCP values and are not written to disk. Both
credential files are under `~/.config/netcup-cli/`, or under
`$XDG_CONFIG_HOME/netcup-cli/` when `XDG_CONFIG_HOME` is set. See
[Authentication](docs/authentication.md) and
[Configuration](docs/configuration.md) for the full setup guide.

```bash
netcup-cli dns domains list                     # paginated account domains
netcup-cli dns domains list --field fqdn --direction asc --page 2 --per-page 20
netcup-cli dns domains get bücher.example       # exact FQDN lookup; reports CloudDNS status
netcup-cli dns zone get example.com              # classic DNS via Legacy CCP
netcup-cli dns records list example.com          # classic DNS via Legacy CCP
netcup-cli dns records update example.com --file records.json --yes
netcup-cli dns record-types list                  # public REST operation
netcup-cli dns acme list example.com             # CloudDNS via REST
netcup-cli dns changeset apply example.com --file changeset.json --yes
netcup-cli dns revisions list example.com
netcup-cli dns revisions create example.com --yes
netcup-cli dns revisions records add example.com <revision-uuid> --file record.json --yes
netcup-cli dns revisions commit example.com <revision-uuid> --yes
netcup-cli dns ddns update home.example.com --ipv4 192.0.2.10 --ipv6 2001:db8::10 --yes
```

Classic DNS zone and record commands use the Legacy CCP API; domain listing, CloudDNS ACME, changesets, and revisions use the REST API. `dns domains list` accepts optional `--domain-id`, `--fqdn`, `--field domainId|fqdn`, `--direction asc|desc`, `--page`, and `--per-page` filters. Writes never switch backends automatically. Domain names are accepted in Unicode and sent in ASCII IDN form. Dynamic DNS updates only A and/or AAAA records on a CloudDNS-managed domain. Every DNS write asks for confirmation; use `--yes` for scripts. These APIs do not expose domain reseller, registration, transfer, or contact-handle commands. See [DNS command details](docs/commands.md#dns) and [API coverage](docs/api-coverage.md#customer-control-panel-ccp-dns).

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
| `dns` | Manage CCP classic DNS, CloudDNS and Dynamic DNS |
| `tasks` | Manage async tasks |
| `users` | User account, failover IPs, firewall policies |
| `set` `power` `rescue` `iso` `disks` `interfaces` `metrics` `logs` `guest-agent` `user-image` `optimize-storage` | More server operations |
| `update` | Update to latest version from GitHub |
| `completion bash\|zsh\|fish` | Shell completion |

Full documentation: `man netcup-cli`
