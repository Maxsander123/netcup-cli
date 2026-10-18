# Netcup CCP DNS Support Design

**Status:** Approved in chat with domain reselling excluded  
**Date:** 2026-10-18

## Goal

Extend `netcup-cli` with the documented Customer Control Panel (CCP) DNS APIs while preserving its existing Server Control Panel (SCP) commands. The CLI must manage classic DNS zones and records, CloudDNS DNS operations exposed by Netcup's current REST API, and CloudDNS Dynamic DNS updates. Domain reselling, domain registration/transfer, contact handles, and reseller order management are explicitly out of scope.

## API scope and sources of truth

Netcup exposes three relevant non-reseller DNS interfaces:

1. **Legacy CCP DNS API** at `https://ccp.netcup.net/run/webservice/servers/endpoint.php?JSON`. Its documented DNS methods are `login`, `logout`, `infoDnsZone`, `infoDnsRecords`, `updateDnsZone`, and `updateDnsRecords`. It can manage domains using the classic Netcup DNS backend.
2. **Netcup REST API** at `https://api.netcup.com/v1`, authenticated with a bearer API key. Its current OpenAPI document at `/openapi.json` is the authoritative operation contract. The API exposes domain ownership/backend information and CloudDNS-specific DNS operations, including ACME challenge records. A checked-in snapshot and a command-to-operation coverage table make supported operations auditable.
3. **CloudDNS Dynamic DNS API** at `https://customercontrolpanel.de/wsDynDns.php`, which updates A and/or AAAA records for an FQDN with a DynDNS token. It only works for CloudDNS-managed domains.

The legacy API's JSON request format is used; SOAP is not added. The checked-in current OpenAPI snapshot is used to define the exact Netcup REST operations and their argument/response shapes. No reseller API methods are exposed.

## Command design

Add a `dns` command group without changing existing SCP command names:

- `dns domains list` lists domains from the authenticated REST API with its documented filters and pagination. `dns domains get <domain>` looks up a supplied FQDN and indicates CloudDNS eligibility; `isDnsManaged=false` does not prove Legacy eligibility.
- `dns records list <domain>` and `dns records update <domain> --file <json>` provide read/update access to zones and records through the Legacy CCP API. `dns zone get|update` provides explicit zone configuration operations.
- `dns acme list|add|delete <domain> ...` exposes the CloudDNS ACME challenge operations from the REST OpenAPI document.
- `dns ddns update <fqdn>` updates one or both IP families using the CloudDNS Dynamic DNS endpoint.
- A DNS API coverage document maps every supported legacy and REST operation to a named command and records any API operation that is intentionally unsupported, with its reason.

Domain lookup accepts Unicode input and normalizes internationalized names to the API's required ASCII form. The CLI does not guess between APIs for a write: command help and output identify the backend, and unsupported backend/domain combinations return an actionable error. It may use the REST domain lookup to identify the domain and DNS backend before choosing the explicit operation.

## Authentication and configuration

SCP OIDC credentials remain unchanged. CCP DNS credentials are stored separately under the existing XDG `netcup-cli` configuration directory with restrictive file permissions. The legacy CCP configuration contains customer number, Legacy API key, and Legacy API password; its 15-minute session is created for a call/session scope and logged out after use. The Netcup REST API key and CloudDNS DynDNS token are separate settings. Commands may accept credentials from environment variables for automation, but secrets are never printed, included in errors, or returned in normal command output.

Provide named `dns auth` configuration/status commands or clearly documented environment variables so users can configure each API independently. Logging out of SCP does not delete CCP DNS credentials, and clearing one CCP credential type does not alter the others.

## Safety, output, and errors

Read operations do not prompt. DNS zone/record writes and Dynamic DNS updates require interactive confirmation unless `--yes` is supplied. JSON output is available consistently with existing global `--json`. Requests use finite timeouts, validate required input and IP addresses locally, normalize domains safely, and report API status/error messages without credentials. Legacy API sessions are closed even when a request fails.

The CLI warns that DNS changes can affect service availability. It does not silently fall back from the modern API to Legacy API for write operations, since that could route a destructive change to an unintended backend.

## Documentation

Update README, command reference, installation/help text if needed, and add `docs/api-coverage.md` entries for the CCP DNS APIs. Clearly distinguish SCP login from CCP DNS API credentials. Document CloudDNS requirements, classic DNS nameserver requirements, DynDNS's A/AAAA-only behavior, and the absence of domain-reseller functions.

## Acceptance criteria

1. All documented Legacy CCP DNS operations are available through named CLI commands; the API's login/logout lifecycle is handled safely.
2. Every supported DNS operation in the checked-in Netcup REST OpenAPI snapshot maps to a named CLI command; a generic HTTP passthrough is not used. The REST domain list operation is exposed with its documented filters and pagination.
3. CloudDNS DynDNS supports IPv4 only, IPv6 only, or both, and validates the supplied addresses.
4. CCP DNS credentials are isolated from SCP OIDC credentials and from each other, stored with restrictive permissions, and never printed.
5. DNS writes confirm interactively by default and support explicit `--yes` for automation.
6. Existing SCP commands and authentication behavior remain intact.
7. Documentation and API coverage match the implemented command tree. No live state-changing Netcup operation is used for local validation.

## Validation approach

Validate command-to-schema coverage offline against the checked-in Netcup REST OpenAPI snapshot and the documented legacy DNS method list. Review generated help and documentation for consistency, inspect credential and error-output paths, and run offline syntax/package checks. Do not invoke authenticated read or write operations against a real Netcup account during local validation.
