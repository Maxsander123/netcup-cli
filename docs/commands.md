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
