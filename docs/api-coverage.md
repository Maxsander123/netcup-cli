# API Coverage

## Server Control Panel (SCP)

The repository-root `openapi.json` is the SCP contract. Its existing command inventory follows. The separate CCP DNS contract and proposed command mapping are below it.

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
| GET | /servers | `servers list` |
| GET | /servers/{serverId} | `servers get` |
| PATCH | /servers/{serverId} | `servers update` |
| POST | /servers/{serverId}/power | `servers power` |
| GET | /servers/{serverId}/gpu-driver | `servers gpu-driver` |
| GET | /servers/{serverId}/guest-agent | `servers guest-agent get` |
| GET | /servers/{serverId}/guest-agent/status | `servers guest-agent status` |
| GET | /servers/{serverId}/logs | `servers logs list` |
| GET | /servers/{serverId}/rescue | `servers rescue get` |
| POST | /servers/{serverId}/rescue/activate | `servers rescue activate` |
| POST | /servers/{serverId}/rescue/deactivate | `servers rescue deactivate` |
| POST | /servers/{serverId}/storage/optimize | `servers storage optimize` |
| GET | /servers/{serverId}/disks | `servers disks list` |
| GET | /servers/{serverId}/disks/supported-drivers | `servers disks supported-drivers` |
| GET | /servers/{serverId}/disks/{diskId} | `servers disks get` |
| PATCH | /servers/{serverId}/disks/{diskId} | `servers disks update` |
| POST | /servers/{serverId}/disks/{diskId}/format | `servers disks format` |
| GET | /servers/{serverId}/image/flavours | `servers image flavours` |
| POST | /servers/{serverId}/image/install | `servers image install` |
| POST | /servers/{serverId}/image/install-user | `servers image install-user` |
| GET | /servers/{serverId}/iso | `servers iso get` |
| POST | /servers/{serverId}/iso/attach | `servers iso attach` |
| POST | /servers/{serverId}/iso/detach | `servers iso detach` |
| GET | /servers/{serverId}/iso/available | `servers iso available` |
| GET | /servers/{serverId}/interfaces | `servers interfaces list` |
| POST | /servers/{serverId}/interfaces | `servers interfaces create` |
| GET | /servers/{serverId}/interfaces/{interfaceId} | `servers interfaces get` |
| PATCH | /servers/{serverId}/interfaces/{interfaceId} | `servers interfaces update` |
| DELETE | /servers/{serverId}/interfaces/{interfaceId} | `servers interfaces delete` |
| GET | /servers/{serverId}/interfaces/{interfaceId}/firewall | `servers interfaces firewall get` |
| PUT | /servers/{serverId}/interfaces/{interfaceId}/firewall | `servers interfaces firewall update` |
| POST | /servers/{serverId}/interfaces/{interfaceId}/firewall/reapply | `servers interfaces firewall reapply` |
| POST | /servers/{serverId}/interfaces/{interfaceId}/firewall/restore-copied-policies | `servers interfaces firewall restore-copied-policies` |
| GET | /servers/{serverId}/metrics/cpu | `servers metrics cpu` |
| GET | /servers/{serverId}/metrics/disk | `servers metrics disk` |
| GET | /servers/{serverId}/metrics/network | `servers metrics network` |
| GET | /servers/{serverId}/metrics/network-packets | `servers metrics network-packets` |
| GET | /servers/{serverId}/snapshots | `servers snapshots list` |
| POST | /servers/{serverId}/snapshots | `servers snapshots create` |
| GET | /servers/{serverId}/snapshots/{snapshotId} | `servers snapshots get` |
| DELETE | /servers/{serverId}/snapshots/{snapshotId} | `servers snapshots delete` |
| POST | /servers/{serverId}/snapshots/{snapshotId}/export | `servers snapshots export` |
| POST | /servers/{serverId}/snapshots/{snapshotId}/revert | `servers snapshots revert` |
| POST | /servers/{serverId}/snapshots/{snapshotId}/revert/dry-run | `servers snapshots dry-run` |
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
| `servers power` | POST /servers/{serverId}/power |
| `users images upload` | prepare-upload + get-part-url (×N) + complete-upload (or prepare-upload + presigned PUT) |
| `users isos upload` | prepare-upload + get-part-url (×N) + complete-upload (or prepare-upload + presigned PUT) |

## Customer Control Panel (CCP) DNS

The [Netcup REST OpenAPI snapshot](netcup-rest-openapi.json) was fetched from [Netcup's public endpoint](https://api.netcup.com/v1/openapi.json) on 2026-10-18. It declares OpenAPI 3.1.0, API version `2026.0921.153936`, and server `https://api.netcup.com`. SHA-256: `e3e59aab819643e64a2b596c588e48e3f2e729adce022608e73efc71c967a844`. The paths below include `/v1`; clients must not prepend `/v1` twice. This is an **operation inventory and intended CLI mapping**, not a claim that these commands are implemented yet.

REST requests use a bearer API key. `domainId` is an integer of at least 1. `revisionId` and `recordId` are UUIDs. All parameters not identified as optional below are required. The `GET /v1/domain` operation is a filtered domain lookup here: `dns domains get <fqdn>` supplies the optional `fqdn` query filter and selects the matching domain. It is not an account-wide list command.

| Method | REST path | Required path/query and JSON body | Intended CLI command |
|---|---|---|---|
| GET | `/v1/dns/recordType` | None | `dns record-types list` |
| GET | `/v1/domain` | Query `fqdn` for CLI lookup; API also permits optional `domainId`, `field` (`domainId` or `fqdn`), `direction` (`asc` or `desc`), `page`, `perPage`. No body. | `dns domains get <fqdn>` |
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

| Action | Required `param` keys | Intended CLI command |
|---|---|---|
| `login` | `customernumber`, `apikey`, `apipassword` | Internal session setup for Legacy DNS commands |
| `logout` | `customernumber`, `apikey`, `apisessionid` | Internal session cleanup after Legacy DNS commands |
| `infoDnsZone` | `customernumber`, `apikey`, `apisessionid`, `domainname` | `dns zone get <domain>` |
| `infoDnsRecords` | `customernumber`, `apikey`, `apisessionid`, `domainname` | `dns records list <domain>` |
| `updateDnsZone` | `customernumber`, `apikey`, `apisessionid`, `domainname`, `dnszone` | `dns zone update <domain> --file <json>` |
| `updateDnsRecords` | `customernumber`, `apikey`, `apisessionid`, `domainname`, `dnsrecordset` | `dns records update <domain> --file <json>` |

### Coverage boundary

All 17 operations in this REST snapshot are DNS or domain lookup operations and appear above. It contains **no non-DNS REST operations**; any such operations introduced in a later schema are outside this DNS feature until separately reviewed. Domain lookup is included solely to resolve a supplied FQDN and determine DNS eligibility. The Legacy CCP reseller actions `createDomain`, `updateDomain`, `transferDomain`, `changeOwnerDomain`, `cancelDomain`, `infoDomain`, `getAuthcodeDomain`, `listallDomains`, `createHandle`, `updateHandle`, `deleteHandle`, `infoHandle`, `listallHandle`, `priceTopleveldomain`, `poll`, and `ackpoll` are all outside scope. They manage domain ownership, commercial lifecycle, contacts, reseller pricing, or reseller messages rather than DNS zone records, and some require a reseller contract. The shared `login` and `logout` actions are used only to scope the DNS calls. No reseller action maps to a CLI command here. CloudDNS Dynamic DNS uses a separate endpoint and token, so it is not represented by this REST OpenAPI snapshot; its intended command is `dns ddns update <fqdn>`.
