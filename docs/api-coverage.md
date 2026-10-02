# API Coverage

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
