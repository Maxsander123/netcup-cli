# Command Reference

All commands accept `--help` for usage details. Pass `--json` to `netcup-cli` for JSON output.

## auth

```
netcup-cli auth login           Login via browser (device code, no password)
netcup-cli auth logout          Remove local credentials
netcup-cli auth revoke          Revoke token with provider and remove credentials
netcup-cli auth show            Show login status
```

## api

```
netcup-cli api ping             Ping the SCP API
netcup-cli api openapi get      Download the live OpenAPI schema
netcup-cli api openapi explore  List all operations in the schema
```

## maintenance

```
netcup-cli maintenance info     Get maintenance info [DEPRECATED, removed 2026-12-31]
```

## rdns

```
netcup-cli rdns ipv4 get <IP>             Get IPv4 rDNS
netcup-cli rdns ipv4 set <IP> --hostname  Set IPv4 rDNS
netcup-cli rdns ipv4 delete <IP>          Delete IPv4 rDNS

netcup-cli rdns ipv6 get <IP>             Get IPv6 rDNS
netcup-cli rdns ipv6 set <IP> --hostname  Set IPv6 rDNS
netcup-cli rdns ipv6 delete <IP>          Delete IPv6 rDNS
```

## dns

CCP DNS credentials are separate from SCP `login`. Run `dns auth set legacy`, `dns auth set rest`, or `dns auth set ddns` to save one API's credentials in a mode-0600 CCP file. Secret prompts do not echo. For non-interactive API use, set `NETCUP_CCP_CUSTOMER_NUMBER`, `NETCUP_CCP_LEGACY_API_KEY`, `NETCUP_CCP_LEGACY_API_PASSWORD`, `NETCUP_API_KEY`, and/or `NETCUP_DDNS_TOKEN`; these override stored values without saving them. `dns auth show` returns only configured booleans. `dns auth clear` changes only stored CCP settings. SCP credentials remain separate.

Every DNS write needs interactive confirmation or `--yes` / `-y`. Read commands do not prompt. The global `--json` option emits JSON. Unicode FQDNs are converted to ASCII IDN names. CloudDNS REST commands require a CloudDNS-managed domain; classic zone and record commands use the Legacy CCP API, whose domains must use the classic DNS backend. Writes do not fall back between backends. Dynamic DNS changes A and/or AAAA records only.

```text
netcup-cli dns auth show
netcup-cli dns auth set legacy [--customer-number NUMBER] [--yes]
netcup-cli dns auth set rest [--yes]
netcup-cli dns auth set ddns [--yes]
netcup-cli dns auth clear legacy|rest|ddns|all [--yes]

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

The Legacy `zone update` file must be a JSON object used as `dnszone`; `records update` must be a JSON object used as `dnsrecordset`. Obtain the current structure with `zone get` or `records list`, edit it, then submit it. For CloudDNS, a changeset file contains boolean `autoCommit` and `strict`, with optional `create` and `delete` arrays. Each record input needs `name`, `type`, `rdata`, and positive integer `ttl`; for example `{"name":"www","type":"A","rdata":"192.0.2.10","ttl":300}`. Create a revision, edit its records or apply a changeset, then commit the revision. IDs are UUIDs. ACME values are 43-character base64url strings; `scope` is `@` or a hostname label. Dynamic DNS needs at least one IP address and a DynDNS token.

`dns domains get` resolves only the supplied FQDN. Its `isDnsManaged=true` result indicates CloudDNS management; `false` does not establish Legacy DNS eligibility. Check the domain's DNS backend before using Legacy commands. An account-wide domain list and domain reseller operations are outside the documented DNS API scope. The public record-type list needs no API key or saved credential file; the other REST operations use the bearer REST API key. Classic DNS requires the appropriate nameserver/backend setup, and CloudDNS commands require CloudDNS management for that domain.

## servers

```
netcup-cli servers list [--page N] [--page-size N]
netcup-cli servers get <SERVER_ID>
netcup-cli servers update <SERVER_ID> [--nickname NAME] [--state-option STATE] [--body-file FILE] [--yes]
netcup-cli servers power <SERVER_ID> <start|stop|reboot|hard-stop|hard-reboot> [--yes]
netcup-cli servers gpu-driver <SERVER_ID>
netcup-cli servers guest-agent get <SERVER_ID>
netcup-cli servers guest-agent status <SERVER_ID>
netcup-cli servers logs list <SERVER_ID>
netcup-cli servers rescue get <SERVER_ID>
netcup-cli servers rescue activate <SERVER_ID> [--yes]
netcup-cli servers rescue deactivate <SERVER_ID> [--yes]
netcup-cli servers storage optimize <SERVER_ID>

netcup-cli servers disks list <SERVER_ID>
netcup-cli servers disks get <SERVER_ID> <DISK_ID>
netcup-cli servers disks update <SERVER_ID> <DISK_ID> --body-file FILE
netcup-cli servers disks supported-drivers <SERVER_ID>
netcup-cli servers disks format <SERVER_ID> <DISK_ID> --filesystem FS [--yes]

netcup-cli servers image flavours <SERVER_ID>
netcup-cli servers image install <SERVER_ID> --image-id ID [--disk-id ID] [--hostname H] [--yes]
netcup-cli servers image install-user <SERVER_ID> --image-id ID [--disk-id ID] [--yes]

netcup-cli servers iso get <SERVER_ID>
netcup-cli servers iso attach <SERVER_ID> --iso-id ID
netcup-cli servers iso detach <SERVER_ID>
netcup-cli servers iso available <SERVER_ID>

netcup-cli servers interfaces list <SERVER_ID>
netcup-cli servers interfaces create <SERVER_ID> --body-file FILE
netcup-cli servers interfaces get <SERVER_ID> <IFACE_ID>
netcup-cli servers interfaces update <SERVER_ID> <IFACE_ID> --body-file FILE [--yes]
netcup-cli servers interfaces delete <SERVER_ID> <IFACE_ID> [--yes]
netcup-cli servers interfaces firewall get <SERVER_ID> <IFACE_ID>
netcup-cli servers interfaces firewall update <SERVER_ID> <IFACE_ID> --body-file FILE [--yes]
netcup-cli servers interfaces firewall reapply <SERVER_ID> <IFACE_ID> [--yes]
netcup-cli servers interfaces firewall restore-copied-policies <SERVER_ID> <IFACE_ID> [--yes]

netcup-cli servers metrics cpu <SERVER_ID> [--from ISO] [--to ISO] [--resolution R]
netcup-cli servers metrics disk <SERVER_ID> [--from ISO] [--to ISO] [--resolution R]
netcup-cli servers metrics network <SERVER_ID> [--from ISO] [--to ISO] [--resolution R]
netcup-cli servers metrics network-packets <SERVER_ID> [--from ISO] [--to ISO] [--resolution R]

netcup-cli servers snapshots list <SERVER_ID>
netcup-cli servers snapshots create <SERVER_ID> --name NAME [--description D]
netcup-cli servers snapshots get <SERVER_ID> <SNAP_ID>
netcup-cli servers snapshots delete <SERVER_ID> <SNAP_ID> [--yes]
netcup-cli servers snapshots export <SERVER_ID> <SNAP_ID>
netcup-cli servers snapshots revert <SERVER_ID> <SNAP_ID> [--yes]
netcup-cli servers snapshots dry-run <SERVER_ID> <SNAP_ID>
```

## tasks

```
netcup-cli tasks list [--page N] [--page-size N] [--status STATUS]
netcup-cli tasks get <TASK_ID>
netcup-cli tasks cancel <TASK_ID> [--yes]
```

## users

```
netcup-cli users get [USER_ID]
netcup-cli users update [USER_ID] --body-file FILE
netcup-cli users logs list [USER_ID]
netcup-cli users ssh-keys list [USER_ID]
netcup-cli users ssh-keys create [USER_ID] --name NAME --public-key KEY
netcup-cli users ssh-keys delete [USER_ID] KEY_ID [--yes]

netcup-cli users failover-ips ipv4 list [USER_ID]
netcup-cli users failover-ips ipv4 route [USER_ID] IP --server-id ID [--yes]
netcup-cli users failover-ips ipv6 list [USER_ID]
netcup-cli users failover-ips ipv6 route [USER_ID] IP --server-id ID [--yes]

netcup-cli users firewall-policies list [USER_ID]
netcup-cli users firewall-policies create [USER_ID] --body-file FILE
netcup-cli users firewall-policies get [USER_ID] POLICY_ID
netcup-cli users firewall-policies update [USER_ID] POLICY_ID --body-file FILE [--yes]
netcup-cli users firewall-policies delete [USER_ID] POLICY_ID [--yes]

netcup-cli users images list [USER_ID]
netcup-cli users images get [USER_ID] IMAGE_ID
netcup-cli users images prepare-upload [USER_ID] --key KEY [--multipart|--single]
netcup-cli users images get-part-url [USER_ID] --upload-id ID --part-number N
netcup-cli users images complete-upload [USER_ID] --upload-id ID --body-file FILE
netcup-cli users images delete [USER_ID] IMAGE_ID [--yes]
netcup-cli users images upload [USER_ID] --file PATH --key KEY [--multipart|--single] [--part-size N]

netcup-cli users isos list [USER_ID]
netcup-cli users isos get [USER_ID] ISO_ID
netcup-cli users isos prepare-upload [USER_ID] --key KEY [--multipart|--single]
netcup-cli users isos get-part-url [USER_ID] --upload-id ID --part-number N
netcup-cli users isos complete-upload [USER_ID] --upload-id ID --body-file FILE
netcup-cli users isos delete [USER_ID] ISO_ID [--yes]
netcup-cli users isos upload [USER_ID] --file PATH --key KEY [--multipart|--single] [--part-size N]

netcup-cli users vlans list [USER_ID]
netcup-cli users vlans get [USER_ID] VLAN_ID
netcup-cli users vlans update [USER_ID] VLAN_ID --body-file FILE [--yes]
```

## vlans

```
netcup-cli vlans get <VLAN_ID>
```

## completion

```
netcup-cli completion bash    Print bash completion script
netcup-cli completion zsh     Print zsh completion script
netcup-cli completion fish    Print fish completion script
```

Add to shell config:
```bash
eval "$(netcup-cli completion bash)"
```
