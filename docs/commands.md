# Command Reference

All commands accept `--help`. Put global options such as `--json` and
`--no-wait` before the command:

```bash
netcup-cli --json dns domains list
netcup-cli --no-wait stop my-server
```

For first-time installation and credentials, see [Installation](installation.md)
and [Authentication](authentication.md). Server commands use SCP login;
`dns` commands use the separate CCP credential setup.

## Main commands

These are the top-level commands in the current CLI. Server operations take a
server ID, nickname, or hostname unless noted.

| Command | Purpose |
|---|---|
| `login`, `logout`, `whoami` | Manage local SCP device-code login |
| `list`, `info <server>` | List servers and show server details |
| `start <server>`, `stop <server>`, `reset <server>` | Change server power state |
| `power <server> <action>` | Use `on`, `off`, `poweroff`, `reset`, `powercycle`, or `suspend` |
| `set <server> [options]` | Change server settings |
| `vnc <server>` | Open the server console |
| `images [server]`, `install <server>` | List OS images and install an OS |
| `snapshot <command>` | Check, list, create, restore, delete, or export snapshots |
| `ssh-key <command>` | List, add, or delete SSH keys |
| `rdns <ipv4\|ipv6> <command>` | Read, set, or delete reverse DNS |
| `dns <group> <command>` | Use CCP classic DNS, CloudDNS REST, or Dynamic DNS |
| `disks <command>`, `interfaces <command>`, `iso <command>` | Manage disks, interfaces, firewall, and ISOs |
| `metrics <type> <server>` | Read CPU, disk, network, or packet metrics |
| `gpu-driver`, `guest-agent`, `logs`, `rescue`, `optimize-storage`, `user-image` | Server utilities |
| `tasks <command>` | List, inspect, or cancel asynchronous tasks |
| `users <command>`, `vlans <command>` | Manage account resources and VLANs |
| `api <command>` | Ping the SCP API or inspect its OpenAPI schema |
| `maintenance info` | Deprecated maintenance endpoint |
| `update`, `completion <shell>` | Update the CLI or print shell completion |

Use the subcommand help for current options, for example `netcup-cli users --help`
or `netcup-cli snapshot --help`.

## CCP DNS setup

First choose the DNS API you need; they use different credentials and do not
fall back to each other:

| DNS command | API | Setup |
|---|---|---|
| `dns zone`, `dns records` | Legacy CCP classic DNS | `netcup-cli dns auth set legacy` |
| `dns domains`, `dns acme`, `dns changeset`, `dns revisions` | CloudDNS REST | `netcup-cli dns auth set rest` |
| `dns ddns` | CloudDNS Dynamic DNS | `netcup-cli dns auth set ddns` |

Each command prompts privately for credentials. `dns auth show` reports only
whether each credential group is configured. `dns auth clear legacy|rest|ddns|all`
removes saved CCP credentials. See [Authentication](authentication.md#ccp-dns-setup)
and [Configuration](configuration.md#environment-variables) for setup details
and environment variables.

## DNS commands

```text
netcup-cli dns auth show
netcup-cli dns auth set legacy [--customer-number NUMBER] [--yes]
netcup-cli dns auth set rest [--yes]
netcup-cli dns auth set ddns [--yes]
netcup-cli dns auth clear legacy|rest|ddns|all [--yes]

netcup-cli dns domains list [--domain-id ID] [--fqdn FQDN] [--field domainId|fqdn] [--direction asc|desc] [--page N] [--per-page N]
netcup-cli dns domains get <fqdn>
netcup-cli dns record-types list

netcup-cli dns zone get <domain>
netcup-cli dns zone update <domain> --file zone.json [--yes]
netcup-cli dns records list <domain>
netcup-cli dns records update <domain> --file records.json [--yes]

netcup-cli dns acme list <fqdn>
netcup-cli dns acme add <fqdn> <scope> <value> [--yes]
netcup-cli dns acme get <fqdn> <scope> <value>
netcup-cli dns acme delete <fqdn> <scope> <value> [--yes]
netcup-cli dns changeset apply <fqdn> --file changeset.json [--yes]

netcup-cli dns revisions list <fqdn> [--field FIELD] [--direction asc|desc] [--page N] [--per-page N]
netcup-cli dns revisions create <fqdn> [--yes]
netcup-cli dns revisions get <fqdn> <revision-uuid>
netcup-cli dns revisions delete <fqdn> <revision-uuid> [--yes]
netcup-cli dns revisions changeset apply <fqdn> <revision-uuid> --file changeset.json [--yes]
netcup-cli dns revisions commit <fqdn> <revision-uuid> [--yes]
netcup-cli dns revisions records list <fqdn> <revision-uuid>
netcup-cli dns revisions records add <fqdn> <revision-uuid> --file record.json [--yes]
netcup-cli dns revisions records get <fqdn> <revision-uuid> <record-uuid>
netcup-cli dns revisions records delete <fqdn> <revision-uuid> <record-uuid> [--yes]

netcup-cli dns ddns update <fqdn> [--ipv4 ADDRESS] [--ipv6 ADDRESS] [--yes]
```

`domains list` returns a paginated account domain list. `domains get` looks up
one exact FQDN. CloudDNS REST commands require a CloudDNS-managed domain;
`isDnsManaged=false` does not prove that the Legacy API can manage the domain.
Classic zone and record commands require the classic DNS backend. Writes ask
for confirmation; `--yes` confirms them in scripts. Domain resale, registration,
transfer, and contact-handle operations are not included.

Legacy update files contain the JSON object expected by the API (`dnszone` for
`zone update`, `dnsrecordset` for `records update`). Read the current structure
first, edit it, then submit it. REST changeset files contain `autoCommit`,
`strict`, and optional `create` and `delete` arrays. A record has `name`,
`type`, `rdata`, and positive integer `ttl`. Revisions can be edited before
they are committed. Dynamic DNS updates A and/or AAAA records and needs at least
one IP address.

## Common examples

```bash
netcup-cli login
netcup-cli list
netcup-cli info my-server
netcup-cli snapshot list my-server
netcup-cli disks list my-server
netcup-cli users get
netcup-cli tasks list --limit 10
netcup-cli completion bash
```

Full CCP DNS API mapping and scope are in [API coverage](api-coverage.md#customer-control-panel-ccp-dns).
