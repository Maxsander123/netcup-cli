# Configuration

## Configuration directory

By default, configuration is stored in `~/.config/netcup-cli/`. Set
`XDG_CONFIG_HOME` to move it to another configuration root; for example, if
`XDG_CONFIG_HOME=/srv/config`, files are stored under
`/srv/config/netcup-cli/`.

| File | Contents | Used by |
|---|---|---|
| `credentials.json` | SCP OIDC refresh token | Server and SCP API commands |
| `ccp-credentials.json` | Legacy CCP, CloudDNS REST, and Dynamic DNS credentials | DNS commands |

Both files are created with owner-only permissions (`0600`). The two
credential groups are independent. `netcup-cli logout` removes the SCP token;
`netcup-cli dns auth clear ...` removes saved CCP values.

## Environment variables

Non-empty environment variables take precedence over saved values. The CLI
does not save environment-only secrets to either credentials file.

| Variable | Used for |
|---|---|
| `XDG_CONFIG_HOME` | Configuration directory root (default `~/.config`) |
| `NETCUP_OIDC_CLIENT_ID` | SCP OIDC client ID (default `scp`) |
| `NETCUP_CCP_CUSTOMER_NUMBER` | Legacy CCP customer number |
| `NETCUP_CCP_LEGACY_API_KEY` | Legacy CCP API key for classic DNS |
| `NETCUP_CCP_LEGACY_API_PASSWORD` | Legacy CCP API password for classic DNS |
| `NETCUP_API_KEY` | CloudDNS REST API key |
| `NETCUP_DDNS_TOKEN` | CloudDNS Dynamic DNS token |

For unattended jobs, provide the variables needed by the command. For example,
`dns domains list` needs `NETCUP_API_KEY`; `dns zone get` and `dns records list`
need the three Legacy variables; `dns ddns update` needs `NETCUP_DDNS_TOKEN`.

## Confirmations

Commands that change server or DNS state ask for confirmation in an
interactive terminal. Add `--yes` or `-y` to confirm explicitly in automation.
The global `--json` option must appear before the command:

```bash
netcup-cli --json list
netcup-cli --json dns domains list
```

In scripts, include `--yes` on every command that asks for confirmation.
Read-only commands do not ask for confirmation.
