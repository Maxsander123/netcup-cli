# API Coverage

## Server Control Panel (SCP)

The repository-root `openapi.json` is the SCP contract. The command column names the current CLI commands. The separate CCP DNS contract and its command mapping follow.

OpenAPI snapshot version: `2026.0923.125530`  
Total operations: 87

| Method | Path | CLI Command |
|--------|------|-------------|
| GET | /ping | `api ping` |
| GET | /openapi.json | `api openapi get` |
| GET | /openapi.json | `api openapi explore` (client-side exploration) |
| GET | /maintenance | `maintenance info` [DEPRECATED, removed 2026-12-31] |
| GET | /rdns/ipv4/{ip} | `rdns ipv4 get` |
| PUT | /rdns/ipv4/{ip} | `rdns ipv4 set` |
| DELETE | /rdns/ipv4/{ip} | `rdns ipv4 delete` |
| GET | /rdns/ipv6/{ip} | `rdns ipv6 get` |
| PUT | /rdns/ipv6/{ip} | `rdns ipv6 set` |
| DELETE | /rdns/ipv6/{ip} | `rdns ipv6 delete` |
| GET | /servers | `list` |
| GET | /servers/{serverId} | `info` |
| PATCH | /servers/{serverId} | `set` |
| POST | /servers/{serverId}/power | `power` |
| GET | /servers/{serverId}/gpu-driver | `gpu-driver` |
| GET | /servers/{serverId}/guest-agent | `guest-agent get` |
| GET | /servers/{serverId}/guest-agent/status | `guest-agent status` |
| GET | /servers/{serverId}/logs | `logs` |
| GET | /servers/{serverId}/rescue | `rescue status` |
| POST | /servers/{serverId}/rescue/activate | `rescue activate` |
| POST | /servers/{serverId}/rescue/deactivate | `rescue deactivate` |
| POST | /servers/{serverId}/storage/optimize | `optimize-storage` |
| GET | /servers/{serverId}/disks | `disks list` |
| GET | /servers/{serverId}/disks/supported-drivers | `disks supported-drivers` |
| GET | /servers/{serverId}/disks/{diskId} | `disks get` |
| PATCH | /servers/{serverId}/disks/{diskId} | Not directly exposed |
| POST | /servers/{serverId}/disks/{diskId}/format | `disks format` |
| GET | /servers/{serverId}/image/flavours | `images <server>` |
| POST | /servers/{serverId}/image/install | `install <server>` |
| POST | /servers/{serverId}/image/install-user | `user-image <server> <image-name>` |
| GET | /servers/{serverId}/iso | `iso status` |
| POST | /servers/{serverId}/iso/attach | `iso attach` |
| POST | /servers/{serverId}/iso/detach | `iso detach` |
| GET | /servers/{serverId}/iso/available | `iso list` |
| GET | /servers/{serverId}/interfaces | `interfaces list` |
| POST | /servers/{serverId}/interfaces | `interfaces create` |
| GET | /servers/{serverId}/interfaces/{interfaceId} | `interfaces get` |
| PATCH | /servers/{serverId}/interfaces/{interfaceId} | `interfaces update` |
| DELETE | /servers/{serverId}/interfaces/{interfaceId} | `interfaces delete` |
| GET | /servers/{serverId}/interfaces/{interfaceId}/firewall | `interfaces firewall get` |
| PUT | /servers/{serverId}/interfaces/{interfaceId}/firewall | `interfaces firewall update` |
| POST | /servers/{serverId}/interfaces/{interfaceId}/firewall/reapply | `interfaces firewall reapply` |
| POST | /servers/{serverId}/interfaces/{interfaceId}/firewall/restore-copied-policies | `interfaces firewall restore-copied-policies` |
| GET | /servers/{serverId}/metrics/cpu | `metrics cpu` |
| GET | /servers/{serverId}/metrics/disk | `metrics disk` |
| GET | /servers/{serverId}/metrics/network | `metrics network` |
| GET | /servers/{serverId}/metrics/network-packets | `metrics packets` |
| GET | /servers/{serverId}/snapshots | `snapshot list` |
| POST | /servers/{serverId}/snapshots | `snapshot create` |
| GET | /servers/{serverId}/snapshots/{snapshotId} | Not directly exposed |
| DELETE | /servers/{serverId}/snapshots/{snapshotId} | `snapshot delete` |
| POST | /servers/{serverId}/snapshots/{snapshotId}/export | `snapshot export` |
| POST | /servers/{serverId}/snapshots/{snapshotId}/revert | `snapshot restore` |
| POST | /servers/{serverId}/snapshots/{snapshotId}/revert/dry-run | `snapshot check` |
| GET | /tasks | `tasks list` |
| GET | /tasks/{taskId} | `tasks get` |
| POST | /tasks/{taskId}/cancel | `tasks cancel` |
| GET | /users/{userId} | `users get` |
| PATCH | /users/{userId} | `users update` |
| GET | /users/{userId}/logs | `users logs list` |
| GET | /users/{userId}/ssh-keys | `users ssh-keys list` |
| POST | /users/{userId}/ssh-keys | `users ssh-keys create` |
| DELETE | /users/{userId}/ssh-keys/{keyId} | `users ssh-keys delete` |
| GET | /users/{userId}/failover-ips/ipv4 | `users failover-ips ipv4 list` |
| POST | /users/{userId}/failover-ips/ipv4/{ip}/route | `users failover-ips ipv4 route` |
| GET | /users/{userId}/failover-ips/ipv6 | `users failover-ips ipv6 list` |
| POST | /users/{userId}/failover-ips/ipv6/{ip}/route | `users failover-ips ipv6 route` |
| GET | /users/{userId}/firewall-policies | `users firewall-policies list` |
| POST | /users/{userId}/firewall-policies | `users firewall-policies create` |
| GET | /users/{userId}/firewall-policies/{policyId} | `users firewall-policies get` |
| PUT | /users/{userId}/firewall-policies/{policyId} | `users firewall-policies update` |
| DELETE | /users/{userId}/firewall-policies/{policyId} | `users firewall-policies delete` |
| GET | /users/{userId}/images | `users images list` |
| GET | /users/{userId}/images/{imageId} | `users images get` |
| POST | /users/{userId}/images/prepare-upload | `users images prepare-upload` |
| GET | /users/{userId}/images/get-part-url | `users images get-part-url` |
| POST | /users/{userId}/images/complete-upload | `users images complete-upload` |
| DELETE | /users/{userId}/images/{imageId} | `users images delete` |
| GET | /users/{userId}/isos | `users isos list` |
| GET | /users/{userId}/isos/{isoId} | `users isos get` |
| POST | /users/{userId}/isos/prepare-upload | `users isos prepare-upload` |
| GET | /users/{userId}/isos/get-part-url | `users isos get-part-url` |
| POST | /users/{userId}/isos/complete-upload | `users isos complete-upload` |
| DELETE | /users/{userId}/isos/{isoId} | `users isos delete` |
| GET | /users/{userId}/vlans | `users vlans list` |
| GET | /users/{userId}/vlans/{vlanId} | `users vlans get` |
| PATCH | /users/{userId}/vlans/{vlanId} | `users vlans update` |
| GET | /vlans/{vlanId} | `vlans get` |

### Convenience commands (built from named operations)

| Convenience command | Operations used |
|--------------------|-----------------|
| `power` | POST /servers/{serverId}/power |
| `users images upload` | prepare-upload + get-part-url (×N) + complete-upload (or prepare-upload + presigned PUT) |
| `users isos upload` | prepare-upload + get-part-url (×N) + complete-upload (or prepare-upload + presigned PUT) |

## Customer Control Panel (CCP) DNS

The [Netcup REST OpenAPI snapshot](netcup-rest-openapi.json) was fetched from [Netcup's public endpoint](https://api.netcup.com/v1/openapi.json) on 2026-10-18. It declares OpenAPI 3.1.0, API version `2026.0921.153936`, and server `https://api.netcup.com`. SHA-256: `e3e59aab819643e64a2b596c588e48e3f2e729adce022608e73efc71c967a844`. The paths below include `/v1`; clients must not prepend `/v1` twice. The 17 REST operations have named client methods in `src/netcup_cli/netcup_dns_api.py` and commands in `src/netcup_cli/commands/dns.py`.

The snapshot declares no security requirement for `GET /v1/dns/recordType`, so the client calls it without an Authorization header. The other 16 operations declare bearer authentication with a Netcup REST API key. `domainId` is an integer of at least 1. `revisionId` and `recordId` are UUIDs. All parameters not identified as optional below are required. The `GET /v1/domain` operation supports both `dns domains list` with the documented filters/pagination and `dns domains get <fqdn>` with an exact FQDN filter. An unfiltered request returns a paginated domain list.

| Method | REST path | Required path/query and JSON body | CLI command |
|---|---|---|---|
| GET | `/v1/dns/recordType` | None | `dns record-types list` |
| GET | `/v1/domain` | Optional query `domainId` (integer ≥1), `fqdn`, `field` (`domainId` or `fqdn`), `direction` (`asc` or `desc`), `page` (integer ≥1), `perPage` (integer ≥1). No body. | `dns domains list [--domain-id ID] [--fqdn FQDN] [--field domainId\|fqdn] [--direction asc\|desc] [--page N] [--per-page N]`; `dns domains get <fqdn>` |
| GET | `/v1/domain/{domainId}/acme/challenge` | Path `domainId`; no body. | `dns acme list <fqdn>` |
| POST | `/v1/domain/{domainId}/acme/challenge` | Path `domainId`; required JSON `scope` (`@` or hostname label), `value` (43 characters matching `[A-Za-z0-9_-]`). | `dns acme add <fqdn> <scope> <value>` |
| GET | `/v1/domain/{domainId}/acme/challenge/{scope}/{value}` | Path `domainId`, `scope`, `value`; no body. | `dns acme get <fqdn> <scope> <value>` |
| DELETE | `/v1/domain/{domainId}/acme/challenge/{scope}/{value}` | Path `domainId`, `scope`, `value`; no body. | `dns acme delete <fqdn> <scope> <value>` |
| POST | `/v1/domain/{domainId}/changeset` | Path `domainId`; required JSON `autoCommit` and `strict` booleans; optional `create` and `delete` arrays of `DnsRecordInput`. | `dns changeset apply <fqdn> --file <json>` |
| GET | `/v1/domain/{domainId}/dns/revision` | Path `domainId`; optional query `field`, `direction` (`asc` or `desc`), `page`, `perPage`; no body. | `dns revisions list <fqdn>` |
| POST | `/v1/domain/{domainId}/dns/revision` | Path `domainId`; no body. | `dns revisions create <fqdn>` |
| GET | `/v1/domain/{domainId}/dns/revision/{revisionId}` | Path `domainId`, `revisionId`; no body. | `dns revisions get <fqdn> <revision-id>` |
| DELETE | `/v1/domain/{domainId}/dns/revision/{revisionId}` | Path `domainId`, `revisionId`; no body. | `dns revisions delete <fqdn> <revision-id>` |
| POST | `/v1/domain/{domainId}/dns/revision/{revisionId}/changeset` | Path `domainId`, `revisionId`; required JSON `autoCommit` and `strict` booleans; optional `create` and `delete` arrays of `DnsRecordInput`. | `dns revisions changeset apply <fqdn> <revision-id> --file <json>` |
| POST | `/v1/domain/{domainId}/dns/revision/{revisionId}/commit` | Path `domainId`, `revisionId`; no body. | `dns revisions commit <fqdn> <revision-id>` |
| GET | `/v1/domain/{domainId}/dns/revision/{revisionId}/record` | Path `domainId`, `revisionId`; no body. | `dns revisions records list <fqdn> <revision-id>` |
| POST | `/v1/domain/{domainId}/dns/revision/{revisionId}/record` | Path `domainId`, `revisionId`; required JSON `name`, `type`, `rdata`, `ttl` (integer at least 1). | `dns revisions records add <fqdn> <revision-id> --file <json>` |
| GET | `/v1/domain/{domainId}/dns/revision/{revisionId}/record/{recordId}` | Path `domainId`, `revisionId`, `recordId`; no body. | `dns revisions records get <fqdn> <revision-id> <record-id>` |
| DELETE | `/v1/domain/{domainId}/dns/revision/{revisionId}/record/{recordId}` | Path `domainId`, `revisionId`, `recordId`; no body. | `dns revisions records delete <fqdn> <revision-id> <record-id>` |

`DnsRecordInput` requires `name`, `type`, `rdata`, and `ttl`. The schema defines the permitted record types as `A`, `AAAA`, `CAA`, `CNAME`, `DS`, `MX`, `NS`, `OPENPGPKEY`, `SRV`, `SMIMEA`, `SSHFP`, `TLSA`, and `TXT`. The REST domain response includes `id`, `fqdn`, and `isDnsManaged`; domain lookup resolves the supplied FQDN to the `domainId` needed by the remaining operations. The OpenAPI schema does not describe a separate domain detail endpoint.

### Legacy CCP JSON DNS actions

Netcup's [Legacy API documentation](https://www.netcup.com/en/helpcenter/documentation/domain/our-api) lists the six DNS/session actions below. The parameter names were checked against its [public WSDL](https://ccp.netcup.net/run/webservice/servers/endpoint.php?WSDL). All are JSON `POST` requests to `https://ccp.netcup.net/run/webservice/servers/endpoint.php?JSON`, with top-level `action` and `param` keys. The WSDL also lists `clientrequestid` on each action for request tracking; it is omitted from the core input summary below. `apisessionid` is returned by `login` and used only for the scoped session.

| Action | Required `param` keys | CLI command |
|---|---|---|
| `login` | `customernumber`, `apikey`, `apipassword` | Internal session setup for Legacy DNS commands |
| `logout` | `customernumber`, `apikey`, `apisessionid` | Internal session cleanup after Legacy DNS commands |
| `infoDnsZone` | `customernumber`, `apikey`, `apisessionid`, `domainname` | `dns zone get <domain>` |
| `infoDnsRecords` | `customernumber`, `apikey`, `apisessionid`, `domainname` | `dns records list <domain>` |
| `updateDnsZone` | `customernumber`, `apikey`, `apisessionid`, `domainname`, `dnszone` | `dns zone update <domain> --file <json>` |
| `updateDnsRecords` | `customernumber`, `apikey`, `apisessionid`, `domainname`, `dnsrecordset` | `dns records update <domain> --file <json>` |

### Coverage boundary

All 17 operations in this REST snapshot are DNS or domain lookup operations and appear above. It contains **no non-DNS REST operations**; any such operations introduced in a later schema are outside this DNS feature until separately reviewed. The REST domain list is a non-reseller operation. `isDnsManaged=false` does not establish that a domain is eligible for the Legacy CCP API. The Legacy CCP reseller actions `createDomain`, `updateDomain`, `transferDomain`, `changeOwnerDomain`, `cancelDomain`, `infoDomain`, `getAuthcodeDomain`, `listallDomains`, `createHandle`, `updateHandle`, `deleteHandle`, `infoHandle`, `listallHandle`, `priceTopleveldomain`, `poll`, and `ackpoll` are all outside scope. They manage domain ownership, commercial lifecycle, contacts, reseller pricing, or reseller messages rather than DNS zone records, and some require a reseller contract. The shared `login` and `logout` actions are used only to scope the DNS calls. No reseller action maps to a CLI command here. CloudDNS Dynamic DNS uses a separate endpoint and token, so it is not represented by this REST OpenAPI snapshot; its command is `dns ddns update <fqdn>`.
