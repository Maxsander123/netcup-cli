# Troubleshooting

## Login issues

**"authorization_pending"** — The browser hasn't completed authentication yet. The CLI continues polling automatically.

**"slow_down"** — The CLI is polling too frequently. It increases the interval automatically.

**"access_denied"** — You denied the login request in the browser. Run `netcup-cli auth login` again.

**"expired_token"** — The device code expired (usually 15 minutes). Run `netcup-cli auth login` again.

**"Token refresh failed"** — Your stored refresh token is no longer valid. Run `netcup-cli auth login` to re-authenticate. The old credentials are not removed automatically until you log in again.

## API errors

**401 Unauthorized** — The access token is invalid or expired. The CLI will try to refresh automatically. If it fails, run `netcup-cli auth login`.

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
netcup-cli servers power 12345 stop --yes
```

## Credentials not found

```
Not logged in. Run 'netcup-cli auth login' first.
```

Run `netcup-cli auth login` to authenticate. The credential file must exist at `~/.config/netcup-cli/credentials.json`.

## Debug

For raw JSON output that may help diagnose issues:

```bash
netcup-cli --json <command>
```
