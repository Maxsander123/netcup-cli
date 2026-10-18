# Netcup CCP DNS Implementation Plan

> **For agentic workers:** Implement this plan task by task in the current checkout. Follow the interfaces below and keep each task independently reviewable.

**Goal:** Add complete documented CCP DNS support for Legacy DNS, CloudDNS REST DNS operations, and CloudDNS Dynamic DNS while retaining all existing SCP behavior; exclude domain reselling.

**Architecture:** Add isolated CCP credential storage and API clients alongside the existing SCP OIDC client. A DNS command group exposes named operations for the Legacy CCP JSON API, the current Netcup REST OpenAPI surface, and the CloudDNS DynDNS endpoint. Keep backend selection explicit for writes, and update the command and API coverage documentation with implementation.

**Tech Stack:** Python 3.10+, Click, requests, Rich, and the existing JSON Schema dependency. Use the documented Legacy CCP JSON protocol; no SOAP client or new runtime dependency.

**Spec:** `docs/superpowers/specs/2026-10-18-netcup-ccp-dns-design.md`

## Global Constraints

- Keep Python support at 3.10+ and use the current project dependencies.
- Preserve current SCP command names, SCP OIDC credentials, and SCP HTTP behavior.
- Store CCP secrets separately from SCP credentials with file mode `0600`; never print or include secrets in API errors.
- Do not add domain reseller actions, domain registration/transfer, contact handles, or reseller polling.
- Use finite HTTP timeouts and ensure Legacy API sessions are logged out after each command operation, including error paths.
- Do not silently send writes to another backend when a domain is unsupported by the selected API.
- Local validation must be offline and must not issue authenticated requests or state changes to Netcup.
- Do not add or run tests as part of this work.

## Review Focus

- Secret values are absent from status output, JSON output, exception text, and debug logs; manually inspect both CCP config serialization and API error handling (Task 2).
- Legacy API logout runs after failed DNS reads and writes as well as successful calls; manually inspect the context-manager/finally path (Task 3).
- Domains on the wrong DNS backend fail with a clear error and do not trigger cross-backend write fallback; inspect command routing (Tasks 4 and 6).
- Unicode domains, multipart suffixes, IPv4-only, IPv6-only, and dual-stack DynDNS inputs are normalized or validated as the spec requires; inspect parsing and request construction (Tasks 4 and 5).
- Non-interactive DNS mutations require `--yes`, while read commands never prompt; inspect the CLI confirmation flow (Task 6).

---

### Task 1: Capture the Netcup DNS API contract

**Files:**
- Create: `docs/netcup-rest-openapi.json`
- Modify: `docs/api-coverage.md`

**Interfaces:**
- Produces: an offline snapshot of `https://api.netcup.com/v1/openapi.json` and an initial operation inventory for DNS and domain lookup.
- Existing contract: `openapi.json` at the repository root describes the SCP API and must remain unchanged.

- [ ] Fetch the current REST OpenAPI document from Netcup's documented API endpoint into `docs/netcup-rest-openapi.json`.
- [ ] Record each DNS-related operation, HTTP method, path, required parameters/body, and intended CLI command in `docs/api-coverage.md`; include the Legacy methods `login`, `logout`, `infoDnsZone`, `infoDnsRecords`, `updateDnsZone`, and `updateDnsRecords`.
- [ ] Mark non-DNS REST operations and all reseller operations out of scope, with reasons, so the coverage boundary is reviewable.
- [ ] Commit the contract snapshot and coverage inventory.

### Task 2: Add isolated CCP credential configuration

**Files:**
- Create: `src/netcup_cli/ccp_config.py`

**Interfaces:**
- Produces: `CCPCredentials`, `load_ccp_credentials() -> CCPCredentials | None`, `save_ccp_credentials(credentials: CCPCredentials) -> None`, and `delete_ccp_credentials() -> None`.
- `CCPCredentials` fields: `customer_number`, `legacy_api_key`, `legacy_api_password`, `rest_api_key`, and `ddns_token`, each optional so the user can configure only APIs they use.
- Existing SCP functions and `Credentials(refresh_token=...)` remain behaviorally unchanged.

- [ ] Add CCP credential loading, secure atomic storage, and deletion under the current XDG `netcup-cli` config directory in a separate `ccp-credentials.json` file.
- [ ] Resolve environment overrides `NETCUP_CCP_CUSTOMER_NUMBER`, `NETCUP_CCP_LEGACY_API_KEY`, `NETCUP_CCP_LEGACY_API_PASSWORD`, `NETCUP_API_KEY`, and `NETCUP_DDNS_TOKEN` without persisting environment values automatically.
- [ ] Keep missing or malformed CCP credentials distinct from the existing SCP login error.
- [ ] Commit credential configuration changes.

### Task 3: Implement the Legacy CCP DNS client

**Files:**
- Create: `src/netcup_cli/legacy_dns.py`

**Interfaces:**
- Produces: `LegacyDnsClient(credentials: CCPCredentials)` with `call(action: str, params: dict[str, object] | None = None) -> dict[str, object]`.
- Supports exactly the documented non-reseller operations: `login`, `logout`, `infoDnsZone`, `infoDnsRecords`, `updateDnsZone`, and `updateDnsRecords`.
- Uses `https://ccp.netcup.net/run/webservice/servers/endpoint.php?JSON`, JSON POST payloads, finite timeouts, and the returned `apisessionid` only in memory.

- [ ] Implement login and authenticated action payload construction with `customernumber`, `apikey`, and session ID in the parameter object expected by the JSON API.
- [ ] Implement response parsing that checks API status and returns useful, secret-free `CLIError` messages for HTTP failures and API-level errors.
- [ ] Add a scoped session/context manager that logs out in `finally` after command work, including when the requested API action fails.
- [ ] Commit the Legacy DNS client.

### Task 4: Implement Netcup REST domain lookup and CloudDNS operations

**Files:**
- Create: `src/netcup_cli/netcup_dns_api.py`
- Modify: `docs/api-coverage.md`

**Interfaces:**
- Produces: `NetcupDnsApiClient(api_key: str)` with named methods for domain lookup and every in-scope DNS operation inventoried from `docs/netcup-rest-openapi.json`; the raw request helper remains private.
- Exposes the REST domain list with its documented filters and pagination, domain lookup by supplied FQDN, and named methods for all 17 DNS/domain lookup operations in the captured snapshot: record types, domains, ACME challenges, changesets, DNS revisions, and revision records.
- Uses bearer authentication at `https://api.netcup.com/v1`, finite timeouts, and the existing `CLIError` pattern.

- [ ] Implement REST transport and API error parsing using the current checked-in OpenAPI contract; do not add `/v1` twice because the paths in the schema already contain it.
- [ ] Implement named client methods for all 17 operations in the snapshot: record-type list; domain lookup; ACME challenge list/create/get/delete; zone changeset apply; revision list/create/get/delete; revision changeset apply and commit; revision-record list/create/get/delete. Keep the HTTP request helper private and document the exact method/path-to-method mapping in module docstrings.
- [ ] Keep credentials out of raised errors and map Netcup's API error codes to concise actionable messages.
- [ ] Commit the REST client and updated coverage mapping.

### Task 5: Implement the CloudDNS Dynamic DNS client

**Files:**
- Create: `src/netcup_cli/ddns.py`

**Interfaces:**
- Produces: `update_ddns(token: str, fqdn: str, *, ipv4: str | None = None, ipv6: str | None = None) -> object`.
- Uses `https://customercontrolpanel.de/wsDynDns.php` with the documented `action=update`, `token`, `fqdn`, and optional address parameters.

- [ ] Reject a request with neither IP address, validate IPv4 and IPv6 with Python's `ipaddress` module, and normalize the FQDN to the API's required domain representation.
- [ ] Implement a finite-timeout request that supports both IP families in one call and turns documented HTTP errors into secret-free CLI errors.
- [ ] Commit the Dynamic DNS client.

### Task 6: Expose DNS commands and update user documentation

**Files:**
- Create: `src/netcup_cli/commands/dns.py`
- Modify: `src/netcup_cli/cli.py`
- Modify: `README.md`
- Modify: `docs/commands.md`
- Modify: `docs/api-coverage.md`
- Modify: `netcup-cli.1`

**Interfaces:**
- Produces: a `dns_group` Click group registered as `netcup-cli dns`.
- Command surface: `dns auth show|set|clear`; `dns domains list|get`; `dns record-types list`; `dns zone get|update`; `dns records list|update`; `dns acme list|add|get|delete`; `dns changeset apply`; `dns revisions list|create|get|delete`; `dns revisions changeset apply`; `dns revisions commit`; `dns revisions records list|add|get|delete`; `dns ddns update`.
- Mutating commands use `confirm_action(..., yes=yes)` and the existing global JSON output convention.

- [ ] Implement `dns auth show|set|clear` for independent CCP credentials, with `set legacy`, `set rest`, and `set ddns` scopes. Prompt for secrets without echoing them; accept the documented environment overrides for non-interactive setup.
- [ ] Implement `dns domains list` with all documented query filters/pagination and `dns domains get <fqdn>` using Netcup REST lookup; present CloudDNS eligibility clearly without inferring Legacy eligibility.
- [ ] Implement Legacy zone/record list and update commands with explicit JSON-file inputs for complex update bodies; use the Legacy API session scope from Task 3.
- [ ] Implement all 17 REST commands from Task 1, including record-type listing, FQDN domain lookup, all ACME challenge operations, changeset apply, revision lifecycle, revision commit, and revision-record operations. Use the operation inventory's exact HTTP parameters and body schemas.
- [ ] Implement `dns ddns update` with `--ipv4`, `--ipv6`, and `--yes`; require at least one address.
- [ ] Register the DNS group without changing existing SCP commands; make read-only operations non-interactive and require confirmation for every DNS mutation.
- [ ] Update README, command reference, API coverage, and man page with credential setup, API/backend limits, IDN handling, DNS write confirmation, record/revision workflows, DDNS A/AAAA behavior, and the explicit absence of reseller operations. Distinguish the public record-type operation, which has no security declaration in the snapshot, from bearer-authenticated REST operations.
- [ ] Review `netcup-cli --help` and DNS subcommand help locally, inspect docs against the snapshot, and commit the completed command/documentation changes.

### Task 7: Baseline review before domain-list follow-up

**Files:**
- Review: all files from Tasks 1–6 (completed before the domain-list follow-up)

- [ ] Compare every in-scope REST OpenAPI operation and Legacy DNS method with `docs/api-coverage.md` and the Click command tree.
- [ ] Review secret-handling, session cleanup, backend mismatch, IDN/IP validation, and non-interactive confirmation paths listed in Review Focus.
- [ ] Inspect the final diff for unintended changes to SCP behavior; record the user's explicit live read from `/v1/domain` separately from local/offline validation.
- [ ] Commit any review corrections and leave the checkout clean.

### Task 8: Expose the documented REST domain list

**Files:**
- Modify: `src/netcup_cli/netcup_dns_api.py`
- Modify: `src/netcup_cli/commands/dns.py`
- Modify: `README.md`
- Modify: `docs/commands.md`
- Modify: `docs/api-coverage.md`
- Modify: `netcup-cli.1`
- Update: this spec and plan to record the verified REST list operation.

**Interfaces:**
- Produces: named `NetcupDnsApiClient.list_domains(...)` and `netcup-cli dns domains list`.
- Uses the already inventoried `GET /v1/domain` operation and only its documented query parameters: `domainId`, `fqdn`, `field`, `direction`, `page`, and `perPage`.

- [ ] Implement argument validation and pass only supplied filters to the existing private REST transport.
- [ ] Expose the command using normal JSON/table output and bearer credentials; it is read-only and must not prompt.
- [ ] Update coverage and user documentation and review local help/diff. Do not make further live API calls or run tests.
- [ ] Commit the change.

### Task 9: Final whole-branch review

**Files:**
- Review: all files from Tasks 1–8

- [ ] Compare every in-scope REST operation and Legacy DNS method with API coverage and the command tree.
- [ ] Review secret handling, session cleanup, backend eligibility, FQDN/IP validation, mutation confirmations, and documentation.
- [ ] Inspect the final diff for SCP regressions and ensure no reseller actions were added.
- [ ] Leave the checkout clean; do not run tests or call Netcup.
