# Netcup CLI Port Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the current inventory CLI with a fully named command-line client for every operation in Netcup's SCP REST OpenAPI schema.

**Architecture:** Split the one-file application into a `src/netcup_cli/` package with shared OIDC, configuration, HTTP, error, and output modules. Implement explicit Click commands by SCP resource, and use a pinned OpenAPI snapshot plus a command-coverage document to keep all 87 routes accounted for.

**Tech Stack:** Python 3.10+, Click, Requests, Rich, `jsonschema`, setuptools, `pyproject.toml` console entry point.

**Spec:** `docs/superpowers/specs/2026-10-02-netcup-cli-design.md`

## Global Constraints

- OpenAPI source is version `2026.0923.125530` (OpenAPI `3.0.3`), containing 87 operations in 11 tags.
- Product, executable, Python package, configuration directory, installer, help, and public documentation use `netcup`/`netcup-cli` names.
- CLI executable is `netcup-cli`; Python import package is `netcup_cli`.
- Credentials live under `$XDG_CONFIG_HOME/netcup-cli/` or `~/.config/netcup-cli/`; refresh-token files use mode `0600` where supported.
- Every OpenAPI operation has a named command; there is no generic HTTP request fallback.
- OIDC uses the SCP discovery metadata and device-code and refresh-token grants.
- Destructive or service-interrupting commands prompt unless `--yes` is supplied.
- Enforce confirmations at every direct mutation command; convenience commands must not be the only guarded path to a risky operation.
- Public README and docs are in English.
- Local validation performs no authenticated API calls and changes no Netcup resources.

## Review Focus

- Device-code denial, expiry, slow-down, and refresh-token rejection: login must stop cleanly, persist no partial credentials, and give a re-login instruction.
- API `401`, `403`, `429`, timeout, or non-JSON error: show a concise operation-aware error, use a non-zero exit, and never show tokens.
- IPv4/IPv6 addresses and reserved characters in path parameters: encode exactly once and preserve the API value.
- Missing or malformed fields in nested JSON bodies: reject locally with a field-specific message before sending the request.
- Non-interactive destructive calls and interrupted multipart uploads: never silently proceed or leak the bearer token to presigned storage URLs.

---

### Task 1: Package scaffold, names, and OpenAPI snapshot

**Files:**
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `openapi.json`
- Create: `src/netcup_cli/__init__.py`
- Create: `src/netcup_cli/__main__.py`
- Create: `src/netcup_cli/cli.py`
- Create: `src/netcup_cli/commands/__init__.py`
- Create: `scripts/install-netcup-cli.sh`

**Interfaces:**
- Produces: `netcup_cli.cli:cli`, a Click root group with `--version`, `--help`, and registered resource groups.
- Produces: `netcup_cli.__version__`, read by the root group and package metadata.

- [ ] **Step 1:** Define project metadata with Python `>=3.10`, dependencies `click`, `requests`, `rich`, and `jsonschema`, and the console script `netcup-cli = netcup_cli.cli:cli`; add `.gitignore` entries for virtual environments, build output, and Python cache files.
- [ ] **Step 2:** Create the importable package, root Click group, module entry point, and version source; confirm `python -m netcup_cli --help` runs and shows the Netcup executable name.
- [ ] **Step 3:** Save the official SCP OpenAPI document as `openapi.json`; confirm its OpenAPI version is `3.0.3`, `info.version` is `2026.0923.125530`, and count is 87 operations.
- [ ] **Step 4:** Implement `scripts/install-netcup-cli.sh` to install the package in a user-owned virtual environment and create a `netcup-cli` launcher; retain the old installer until migration is complete and do not run the installer during local validation.
- [ ] **Step 5:** Keep the old entry point until the resource commands are migrated; search the new root group's help for the Netcup executable and config names.

---

### Task 2: OIDC auth, configuration, HTTP client, and shared output

**Files:**
- Create: `src/netcup_cli/config.py`
- Create: `src/netcup_cli/auth.py`
- Create: `src/netcup_cli/client.py`
- Create: `src/netcup_cli/errors.py`
- Create: `src/netcup_cli/validation.py`
- Create: `src/netcup_cli/output.py`
- Create: `src/netcup_cli/commands/auth.py`
- Modify: `src/netcup_cli/cli.py`

**Interfaces:**
- `Credentials(refresh_token: str)` stores the only credential persisted to disk.
- `TokenSet(access_token: str, refresh_token: str | None)` carries short-lived access and rotated refresh tokens in memory.
- `load_credentials() -> Credentials | None`, `save_credentials(credentials: Credentials) -> None`, and `delete_credentials() -> None` own the XDG config path and permissions.
- `AuthClient.login_device() -> TokenSet`, `AuthClient.refresh(refresh_token: str) -> TokenSet`, and `AuthClient.revoke(refresh_token: str) -> None` use endpoints from SCP OIDC discovery.
- `build_client() -> SCPClient` loads credentials, refreshes access, saves any rotated refresh token, and supplies a bearer-authenticated client to Click context.
- `validate_request_body(method: str, path: str, body: object) -> None` matches the concrete request path to its OpenAPI route template and reports invalid field paths.
- `SCPClient(access_token: str)` owns one access token in process memory; `SCPClient.request(method: str, path: str, *, params: Mapping[str, object] | None = None, json_body: object | None = None) -> object | None` adds the bearer token, applies timeouts, validates JSON bodies against the bundled schema, and parses API responses.
- `SCPClient.upload_presigned(url: str, file_path: Path, *, headers: Mapping[str, str] | None = None) -> str | None` streams file bytes without forwarding the SCP bearer token and returns the response ETag for multipart parts.
- `print_result(value: object, *, as_json: bool = False) -> None` handles JSON and Rich output consistently.

- [ ] **Step 1:** Implement XDG config selection, JSON credential serialization, `0600` permissions, and atomic save/delete behavior.
- [ ] **Step 2:** Implement OIDC discovery at `https://www.servercontrolpanel.de/realms/scp/.well-known/openid-configuration` and device-code polling with `NETCUP_OIDC_CLIENT_ID` override; request `openid offline_access`, obtain the default client id from the first-party SCP web client configuration, and reject login if no refresh token is returned.
- [ ] **Step 3:** Implement refresh and revoke; persist only the refresh token, replace it atomically if the provider rotates it, and keep access tokens in process memory.
- [ ] **Step 4:** Implement `validate_request_body` for OpenAPI `3.0.3`, matching concrete paths to templates, resolving internal `$ref` values, and rejecting malformed JSON or schema-invalid bodies before the SCP resource request.
- [ ] **Step 5:** Implement `SCPClient.request` with base URL `https://www.servercontrolpanel.de/scp-core` and exact OpenAPI paths (including `/api/v1`), safe parameter encoding, request timeouts, JSON response parsing, and typed CLI errors for HTTP failures.
- [ ] **Step 6:** Implement the separate presigned-upload transport; it must not send the SCP Authorization header to the storage host.
- [ ] **Step 7:** Add `auth login`, `logout`, `revoke`, and `show`; inspect `netcup-cli auth --help` and verify login help does not ask for or print a password.
- [ ] **Step 8:** Review device-code denied/expired/slow-down and refresh-token rejected branches; they must not persist partial credentials and must display a re-login instruction.
- [ ] **Step 9:** Review `401`, `403`, `429`, timeout, and non-JSON error handling; messages must identify the operation, return non-zero, and redact credentials.

#### Named command map

Implement each listed command against exactly one method/path in the pinned schema. The power and upload commands marked as conveniences call the underlying named operation commands.

```text
api: ping; openapi get|explore
maintenance: info
rdns: ipv4 get|set|delete; ipv6 get|set|delete
servers: list|get|update|power; gpu-driver; guest-agent get|status; logs list
  rescue get|activate|deactivate; storage optimize
  disks list|update|supported-drivers|get|format
  image install|flavours|install-user
  iso get|attach|detach|available
  interfaces list|create|get|update|delete
  interfaces firewall get|update|reapply|restore-copied-policies
  metrics cpu|disk|network|network-packets
  snapshots list|create|get|delete|export|revert|dry-run
tasks: list|get|cancel
users: get|update; logs list; ssh-keys list|create|delete
  failover-ips ipv4 list|route; ipv6 list|route
  firewall-policies list|create|get|update|delete
  images list|get|prepare-upload|get-part-url|complete-upload|delete|upload
  isos list|get|prepare-upload|get-part-url|complete-upload|delete|upload
  vlans list|get|update
vlans: get
```

`servers power`, `users images upload`, and `users isos upload` are convenience commands built from their underlying named operations; the coverage map associates each HTTP operation with its direct command.

---

### Task 3: Servers, disks, and metrics (20 API operations)

**Files:**
- Create: `src/netcup_cli/commands/servers.py`
- Create: `src/netcup_cli/commands/disks.py`
- Create: `src/netcup_cli/commands/metrics.py`
- Create: `src/netcup_cli/safety.py`
- Modify: `src/netcup_cli/cli.py`

**Interfaces:**
- Resource commands consume `SCPClient` from the Click context and return API response objects for `print_result`.
- `confirm_action(message: str, *, yes: bool, non_interactive_error: str) -> None` handles required prompts centrally.

- [ ] **Step 1:** Register `servers` and implement `servers list`, `get`, and `update` for the matching list, detail, and PATCH routes, taking path/query/body fields from `openapi.json`.
- [ ] **Step 2:** Implement `servers power`, `gpu-driver`, `guest-agent get/status`, `logs list`, `rescue get/activate/deactivate`, and `storage optimize`; enforce confirmation on risky `servers update --state-option` values as well as `servers power`, and on rescue actions that interrupt service.
- [ ] **Step 3:** Implement `servers disks list`, `update`, `supported-drivers`, `get`, and `format`; disk format always confirms unless `--yes` is set.
- [ ] **Step 4:** Implement `servers metrics cpu`, `disk`, `network`, and `network-packets`, including every schema query parameter.
- [ ] **Step 5:** Inspect each command's `--help` for arguments matching the operation schema and confirm no command makes a request while rendering help.

---

### Task 4: Images, ISOs, and snapshots (26 API operations)

**Files:**
- Create: `src/netcup_cli/commands/images.py`
- Create: `src/netcup_cli/commands/isos.py`
- Create: `src/netcup_cli/commands/snapshots.py`
- Create: `src/netcup_cli/uploads.py`
- Modify: `src/netcup_cli/cli.py`

**Interfaces:**
- `upload_file(client: SCPClient, *, resource: Literal["images", "isos"], file_path: Path, key: str, user_id: str, multipart: bool = True, part_size: int = 67_108_864) -> object` uses the `S3Upload` response to select its direct presigned URL or multipart part-URL flow, then completes multipart uploads with returned ETags.
- Each individual prepare, part-URL, complete, and delete operation remains separately callable as its named command.

- [ ] **Step 1:** Implement `servers image install`, `servers image flavours`, and `servers image install-user`; image installation confirms before starting because it formats selected disks.
- [ ] **Step 2:** Implement server ISO `get`, `attach`, `detach`, and `available` commands.
- [ ] **Step 3:** Implement user image operations as `users images list/get/prepare-upload/get-part-url/complete-upload/delete`; `prepare-upload --multipart/--single` maps the API query flag; `delete` confirms before removing stored data; add `users images upload --part-size` (default 64 MiB) to execute the single or multipart flow and collect ETags.
- [ ] **Step 4:** Implement user ISO operations as `users isos list/get/prepare-upload/get-part-url/complete-upload/delete`; `prepare-upload --multipart/--single` maps the API query flag; `delete` confirms before removing stored data; add `users isos upload --part-size` (default 64 MiB) to execute the single or multipart flow and collect ETags.
- [ ] **Step 5:** Implement snapshot `list/create/get/delete/export/revert/dry-run`; delete and revert require confirmation unless `--yes` is set.
- [ ] **Step 6:** Inspect upload failure paths to confirm incomplete uploads report their upload id and part number, and SCP tokens are not sent to presigned URLs.

---

### Task 5: Server networking, rDNS, VLANs, failover IPs, and firewall (28 API operations)

**Files:**
- Create: `src/netcup_cli/commands/networking.py`
- Create: `src/netcup_cli/commands/firewalls.py`
- Modify: `src/netcup_cli/cli.py`

**Interfaces:**
- Commands use `SCPClient.request` and central confirmation handling; IP and MAC values are encoded as path parameters exactly once.

- [ ] **Step 1:** Implement server interfaces `list/create/get/update/delete` and nested firewall `get/update/reapply/restore-copied-policies`; confirm interface changes that can disrupt connectivity, including deletion, and all risky firewall operations.
- [ ] **Step 2:** Implement IPv4 and IPv6 `rdns get/set/delete` commands.
- [ ] **Step 3:** Implement user failover IPv4/IPv6 `list/route` commands, preserving API IDs and route payloads from the schema; confirm route changes that can disrupt connectivity.
- [ ] **Step 4:** Implement user VLAN `list/get/update` and standalone `vlans get`; confirm updates that can disrupt connectivity.
- [ ] **Step 5:** Implement user firewall policy `list/create/get/update/delete`; prompt before policy changes that could interrupt connectivity.
- [ ] **Step 6:** Inspect help and request construction for IPv6 and MAC path parameters, plus the confirmation behavior for firewall updates.
- [ ] **Step 7:** Inspect URL construction to confirm IPv6 literals, IPv4 addresses, and MAC addresses are encoded once and preserve their API values.

---

### Task 6: Users, tasks, maintenance, and OpenAPI operations (13 API operations)

**Files:**
- Create: `src/netcup_cli/commands/users.py`
- Create: `src/netcup_cli/commands/tasks.py`
- Create: `src/netcup_cli/commands/misc.py`
- Modify: `src/netcup_cli/cli.py`

**Interfaces:**
- Commands use the shared `SCPClient`, OIDC config, and output helpers; user IDs are explicit path arguments when required by the schema.

- [ ] **Step 1:** Implement `users get/update/logs list/ssh-keys list/create/delete`; confirm SSH key deletion because it can remove account access.
- [ ] **Step 2:** Implement `tasks list/get/cancel`, including filter and pagination parameters; cancellation prompts if the API task can still be stopped.
- [ ] **Step 3:** Implement `api ping`, `maintenance info`, `api openapi get`, and `api openapi explore` for the four Miscellaneous operations; mark maintenance info deprecated in help.
- [ ] **Step 4:** Register all command groups and preserve shell completion as `netcup-cli completion bash|zsh|fish`.
- [ ] **Step 5:** Inspect `netcup-cli --help` and each resource group's help to confirm all expected groups are visible and the deprecated maintenance note appears.

---

### Task 7: README, documentation, and API coverage map

**Files:**
- Create: `README.md`
- Create: `docs/installation.md`
- Create: `docs/authentication.md`
- Create: `docs/configuration.md`
- Create: `docs/commands.md`
- Create: `docs/api-coverage.md`
- Create: `docs/troubleshooting.md`
- Delete after migration: `netbox-cli.py`
- Delete after migration: `install.sh`
- Modify: `pyproject.toml`
- Modify: `scripts/install-netcup-cli.sh`

**Interfaces:**
- Documentation examples use the installed executable `netcup-cli` and the command/option names shown by Click help.
- `docs/api-coverage.md` has one row per HTTP method and path in `openapi.json`, with the exact named command beside it.

- [ ] **Step 1:** Write the README overview, requirements, installation, device-code quick start, server/rDNS examples, JSON usage, and links to detailed docs; use `https://github.com/Maxsander123/netcup-cli` for source installation examples.
- [ ] **Step 2:** Document token storage, environment overrides, logout/revoke, destructive confirmations, and non-interactive automation.
- [ ] **Step 3:** Document every command and option in `docs/commands.md`, including request JSON file shapes for complex operations.
- [ ] **Step 4:** Build the 87-row method/path-to-command coverage table from the pinned snapshot; include the maintenance deprecation date and explicitly name upload sub-operations.
- [ ] **Step 5:** Align the local `origin` URL with the user-provided `https://github.com/Maxsander123/netcup-cli` target, checking it read-only before any publication; then remove `netbox-cli.py` and `install.sh` after their replacements are complete. All shipping files, package, installer, and product-facing names use Netcup names.
- [ ] **Step 6:** Search shipping files for stale executable, package, config, and product names; compare README examples against the actual CLI help. Keep any old-name references limited to migration history and this plan's deletion record.
- [ ] **Step 7:** Document device-code failures, API errors, upload recovery information, and non-interactive confirmation requirements in `docs/troubleshooting.md`.

---

### Task 8: Offline release review

**Files:**
- Review: all `src/netcup_cli/` files
- Review: `README.md`, `docs/`, `openapi.json`, and `pyproject.toml`

**Interfaces:**
- No live Netcup credentials or resource changes are needed for this review.

- [ ] **Step 1:** Run `python -m compileall src/netcup_cli`; expected: no syntax errors.
- [ ] **Step 2:** Run `python -m netcup_cli --help` and each top-level resource `--help`; expected: command tree and version use only Netcup CLI names.
- [ ] **Step 3:** Compare every OpenAPI method/path to the coverage map; expected: exactly 87 mapped operations, no duplicates or omissions.
- [ ] **Step 4:** Run `git diff --check` and a tracked-file search for old product identifiers; expected: clean formatting and no stale product names.
- [ ] **Step 5:** Confirm no command was run against an authenticated Netcup account and no credentials are present in tracked files.
- [ ] **Step 6:** Inspect non-interactive mutation handling; destructive actions must exit with an explanation unless `--yes` is present.
