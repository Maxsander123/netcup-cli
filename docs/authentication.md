# Authentication

netcup-cli uses Netcup's OIDC device-code grant. No password is ever entered into the CLI.

## Login

```bash
netcup-cli auth login
```

The CLI prints a URL. Open it in your browser, authenticate with your Netcup account, then return to the terminal. The CLI polls for completion automatically.

## Token storage

Only the refresh token is stored on disk at:

```
~/.config/netcup-cli/credentials.json   (mode 0600)
```

The path follows `$XDG_CONFIG_HOME/netcup-cli/` when set. Access tokens are kept in memory only and never written to disk.

## Logout and revocation

```bash
netcup-cli auth logout   # Delete local credentials only
netcup-cli auth revoke   # Revoke token with Netcup OIDC, then delete local credentials
```

## Status

```bash
netcup-cli auth show
```

## Non-interactive automation

For scripts and CI, log in interactively once to create the credential file. Subsequent runs use the stored refresh token automatically — no further login needed unless the token expires or is revoked.

## Environment overrides

Set `NETCUP_OIDC_CLIENT_ID` to override the OIDC client identifier (default: `scp`).

## Failure handling

- **authorization_pending** — still waiting for browser; CLI continues polling.
- **slow_down** — polling too fast; CLI increases the interval.
- **access_denied** / **expired_token** — login fails with a clear message; no credentials are saved.
- **Refresh token rejected** — run `netcup-cli auth login` to re-authenticate.
