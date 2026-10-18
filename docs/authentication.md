# Authentication

SCP server commands and CCP DNS commands authenticate separately. You do not
need to configure DNS credentials to use SCP, or sign in to SCP to use DNS.

## SCP server access

The CLI uses Netcup's OIDC device-code login. It never asks for your Netcup
account password.

```bash
netcup-cli login
netcup-cli whoami
```

Open the URL printed by `login`, enter the displayed device code, and finish
sign-in in the browser. The CLI waits for the browser step to finish and saves
the refresh token locally. Access tokens stay in memory.

```bash
netcup-cli logout
```

`logout` removes the local refresh token. It does not revoke the token with
Netcup. The SCP credential file is
`$XDG_CONFIG_HOME/netcup-cli/credentials.json`, or
`~/.config/netcup-cli/credentials.json` when `XDG_CONFIG_HOME` is unset.

## CCP DNS setup

Choose credentials for the API behind the DNS command you want to use:

| Credentials | Used by | Values required |
|---|---|---|
| Legacy CCP | `dns zone` and `dns records` | Customer number, Legacy API key, Legacy API password |
| CloudDNS REST | `dns domains`, `dns acme`, `dns changeset`, `dns revisions` | CloudDNS REST API key |
| CloudDNS Dynamic DNS | `dns ddns` | Dynamic DNS token |

For each API, run its setup command in a terminal. Secret values are prompted
without echoing them and are saved in the separate CCP credential file:

```bash
netcup-cli dns auth set legacy
netcup-cli dns auth set rest
netcup-cli dns auth set ddns
```

The Legacy setup asks for the customer number, API key, and API password. REST
and Dynamic DNS setup each ask for that API's key or token. Saving credentials
requires confirmation. Add `--yes` (or `-y`) to confirm the save in scripts;
for non-interactive use, environment variables are usually simpler.

Check which credential groups are configured without displaying secret values:

```bash
netcup-cli dns auth show
```

Remove saved credentials for one API, or all CCP APIs:

```bash
netcup-cli dns auth clear legacy
netcup-cli dns auth clear rest
netcup-cli dns auth clear ddns
netcup-cli dns auth clear all
```

These commands only change CCP DNS credentials. They do not affect SCP login.
Environment variables take precedence over saved CCP values; clearing a saved
value does not unset an environment variable.

## Non-interactive use

Set the environment variables required for the API you use. See
[Configuration](configuration.md#environment-variables) for the full list.
The CLI reads them for API calls but does not copy them into the credential
file.

## Login troubleshooting

- `authorization_pending`: finish sign-in in the browser; the CLI keeps polling.
- `slow_down`: the CLI increases its polling interval automatically.
- `access_denied`: approve the login request or run `netcup-cli login` again.
- `expired_token`: the device code expired; run `netcup-cli login` again.
- Refresh token rejected: run `netcup-cli login` to authenticate again.
