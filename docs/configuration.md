# Configuration

## Credential file

`~/.config/netcup-cli/credentials.json` (or `$XDG_CONFIG_HOME/netcup-cli/credentials.json`)

Created automatically on first login. Contains only the refresh token. File permissions are set to `0600`.

## Environment variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `XDG_CONFIG_HOME` | `~/.config` | Override the config directory root |
| `NETCUP_OIDC_CLIENT_ID` | `scp` | Override the OIDC client ID |

## JSON output

Pass `--json` before any command to get machine-readable output:

```bash
netcup-cli --json servers list
```

## Destructive command confirmations

Destructive commands prompt for confirmation unless `--yes` / `-y` is supplied. In a non-interactive context (no TTY), the command exits with an error unless `--yes` is set.

Commands that require `--yes` for non-interactive use:
- `servers power` (stop, reboot, hard-stop, hard-reboot)
- `servers rescue activate`, `deactivate`
- `servers disks format`
- `servers image install`, `install-user`
- `servers snapshots delete`, `revert`
- `servers interfaces delete`, `update`, `firewall update`, `reapply`, `restore-copied-policies`
- `users ssh-keys delete`
- `users failover-ips ipv4 route`, `ipv6 route`
- `users firewall-policies update`, `delete`
- `users images delete`, `users isos delete`
- `tasks cancel`
