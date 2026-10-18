# Troubleshooting

## Login issues

**"authorization_pending"** — The browser hasn't completed authentication yet. The CLI continues polling automatically.

**"slow_down"** — The CLI is polling too frequently. It increases the interval automatically.

**"access_denied"** — You denied the login request in the browser. Run `netcup-cli login` again.

**"expired_token"** — The device code expired (usually 15 minutes). Run `netcup-cli login` again.

**"Token refresh failed"** — Your stored refresh token is no longer valid. Run `netcup-cli login` to authenticate again.

## API errors

**401 Unauthorized** — The access token is invalid or expired. The CLI will try to refresh automatically. If it fails, run `netcup-cli login`.

**403 Forbidden** — Your account does not have permission for this operation. Check your Netcup account permissions.

**429 Too Many Requests** — You are being rate-limited. Wait a moment and try again.

**Non-JSON response** — The API returned an unexpected format. This may indicate a temporary service issue. Check https://www.servercontrolpanel.de for status.

## Upload failures

If an upload fails partway through:
- Note the `uploadId` shown in the error message.
- You can resume or complete the upload using `users images complete-upload --upload-id <ID>` with the ETags from completed parts.
- Incomplete uploads do not consume quota but should be completed or abandoned.

## Non-interactive use

If you see "This operation requires confirmation. Re-run with --yes", the command is destructive and requires explicit confirmation. Add `--yes` to the command for automation:

```bash
netcup-cli stop 12345 --yes
netcup-cli power 12345 poweroff --yes
```

## Credentials not found

```
Not logged in. Run 'netcup-cli login' first.
```

Run `netcup-cli login` to authenticate. The SCP credential file is
`~/.config/netcup-cli/credentials.json`, or `$XDG_CONFIG_HOME/netcup-cli/credentials.json`
when `XDG_CONFIG_HOME` is set.

## DNS credentials

SCP login does not configure CCP DNS. Run `netcup-cli dns auth show` to see
which DNS credential groups are configured. Use `netcup-cli dns auth set legacy`,
`netcup-cli dns auth set rest`, or `netcup-cli dns auth set ddns` for the API
required by your command.
The REST domain list needs a REST API key; classic zone and record commands
need Legacy CCP credentials; Dynamic DNS needs its own token. See
[Authentication](authentication.md#ccp-dns-setup).

If a CloudDNS command says a domain is not managed by CloudDNS, check the
domain's DNS backend. Classic `zone` and `records` commands use the Legacy API
and do not automatically fall back to CloudDNS or change the domain backend.

## Debug

For raw JSON output that may help diagnose issues:

```bash
netcup-cli --json <command>
```
