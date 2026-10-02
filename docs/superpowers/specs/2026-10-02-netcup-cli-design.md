# Netcup CLI port design

**Status:** Draft for review<br>
**Date:** 2026-10-02

## Goal

Turn the current one-file CLI into a real `netcup-cli` for Netcup's Server Control Panel (SCP) REST API. The product, command, package, configuration, installer, source files, and public documentation use Netcup names. Every operation in the current SCP OpenAPI schema is available through a named CLI command. There is no generic HTTP request command standing in for missing operations.

The CLI supports both interactive use and scripts. It prints readable terminal output by default and provides JSON output for automation. It never needs a Netcup account password in the CLI.

## Repository findings and API source of truth

The implementation checkout currently has two tracked files: a single Python CLI script and a shell installer. The source contains inventory features such as racks, devices, and power feeds, which do not exist as resources in the SCP API. Those commands will be replaced by commands matching the SCP resource model.

The SCP OpenAPI document is the contract for routes, parameters, request bodies, and responses. The public schema retrieved for this design is version `2026.0923.125530`, with 87 operations in 11 tags. Its server URL is `/scp-core`; its paths include `/api/v1`. A checked-in `openapi.json` snapshot and a generated coverage document make the command-to-operation mapping reviewable. A schema refresh must update the snapshot, named-command mapping, coverage document, and public docs together.

The API security scheme uses OpenID Connect. Netcup's discovery metadata advertises device-code and refresh-token grants. The CLI uses the discovery document for authorization, token, device authorization, and revocation endpoints rather than embedding those endpoint URLs throughout command modules.

This project targets the SCP REST API only. Netcup's separate legacy SOAP web service and CCP domain/DNS APIs are outside this port.

## Command design

Every OpenAPI operation gets a deliberate, named command grouped by SCP resource. The command tree includes:

- `auth` for login, logout, token revocation, and credential status.
- `servers` for server listing/details, power and attributes, disks, interfaces, firewall, ISO, metrics, rescue, snapshots, and storage operations.
- `rdns` for IPv4 and IPv6 reverse DNS.
- `tasks` for listing, lookup, and cancellation.
- `users` for user data, logs, failover IPs, firewall policies, images, ISOs, SSH keys, and VLANs.
- `vlans`, `maintenance`, and `api` for the standalone VLAN, maintenance, ping, OpenAPI, and API-explorer operations.

Path and query parameters become named arguments or options. Simple request fields become typed options. Complex request bodies are accepted as JSON files and validated against their OpenAPI schemas. Image and ISO uploads have named commands for each API operation plus convenience commands that perform the documented upload sequence. Responses support readable tables and `--json` output.

Command names should describe Netcup SCP resources and actions, not the inventory concepts in the previous implementation. `docs/api-coverage.md` lists every OpenAPI method and path beside its command. Deprecated operations remain callable while present in the schema and carry a deprecation note; the current maintenance endpoint is marked for removal by 2026-12-31.

## Package, authentication, and HTTP client

The single script becomes a `src/netcup_cli/` Python package with separate modules for configuration, authentication, the HTTP client, output formatting, and resource command groups. `pyproject.toml` defines the `netcup-cli` executable. The installer is renamed to `install-netcup-cli.sh` and delegates to the same package entry point.

The HTTP client uses the SCP base URL and API paths from the OpenAPI contract, sends OIDC bearer access tokens, applies request timeouts, and converts HTTP/API failures into concise CLI errors with non-zero exit codes. It does not print tokens or credential contents. The command reference documents response pagination, when the API exposes it, and how JSON bodies are supplied.

`netcup-cli auth login` uses OIDC device authorization and displays the verification URL and user code. Refresh tokens are stored under `$XDG_CONFIG_HOME/netcup-cli/` or `~/.config/netcup-cli/` in a file restricted to the current user (`0600` where supported). Access tokens stay in memory. Logout deletes local credentials; revoke also asks the OIDC provider to revoke the refresh token. The OIDC client identifier follows the value used by the first-party SCP web client and can be overridden with `NETCUP_OIDC_CLIENT_ID`.

## Safety and errors

Commands that can interrupt service or destroy data prompt before acting. This includes power-off/reset operations, disk formatting, image installation, snapshot deletion/revert, and destructive firewall changes. `--yes` skips the prompt for deliberate automation. Read-only commands never prompt.

Authentication failures explain how to log in again. Permission failures identify the denied operation without exposing tokens. API error bodies are summarized safely; raw stack traces are only shown with an explicit debug option. The CLI does not perform live Netcup operations during local development validation.

## Documentation and names

The public README and documentation are written in English, matching the repository's code and command vocabulary. They cover installation, requirements, device-code login, credential storage, command examples, JSON output, destructive-action confirmations, troubleshooting, and the exact SCP API surface.

The project adds `docs/` pages for authentication/configuration, the command reference, and API coverage. All project-facing executable, Python package, config-directory, installer, docs, and CLI help names use `netcup`/`netcup-cli`. The README makes clear that this is a command-line client for Netcup's SCP REST API.

## Acceptance criteria

1. Each of the 87 operations in the checked-in OpenAPI snapshot maps to a named CLI command; no operation is accessible only through a generic HTTP passthrough.
2. The command tree follows Netcup SCP resources, and unsupported inventory-only commands are absent.
3. Device-code login, refresh, logout, and revocation use the OIDC discovery metadata and keep credentials out of the repository and terminal output.
4. Destructive and service-interrupting actions require confirmation unless `--yes` is supplied.
5. Human-readable and JSON output work for list/detail operations and API errors produce useful non-zero exits.
6. README, command reference, API coverage, package metadata, installer, and help text consistently use Netcup CLI names and agree on supported operations.
7. Local validation does not make authenticated API calls or change any Netcup resource.

## Validation approach

Review the explicit command-to-operation coverage against the bundled OpenAPI snapshot, inspect generated help and documentation for naming/argument consistency, and perform offline syntax and packaging checks. Do not validate by invoking state-changing Netcup API operations.
