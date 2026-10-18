"""CCP DNS commands, grouped by the API that performs each operation."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

import click

from netcup_cli.ccp_config import (
    CCPCredentials,
    delete_ccp_credentials,
    load_ccp_credentials,
    load_stored_ccp_credentials,
    save_ccp_credentials,
)
from netcup_cli.ddns import update_ddns
from netcup_cli.errors import CLIError
from netcup_cli.legacy_dns import LegacyDnsClient
from netcup_cli.netcup_dns_api import NetcupDnsApiClient
from netcup_cli.output import print_result
from netcup_cli.safety import confirm_action


def _json(ctx: click.Context) -> bool:
    return bool(ctx.find_root().obj.get("json", False))


def _show(ctx: click.Context, value: object) -> None:
    print_result(value, as_json=_json(ctx))


def _fqdn(value: str) -> str:
    """Normalize a complete Unicode DNS name for both CCP backends."""
    if not value or value != value.strip():
        raise CLIError("Supply a valid fully qualified domain name.")
    try:
        name = value.rstrip(".").encode("idna").decode("ascii").lower()
    except UnicodeError:
        raise CLIError("Supply a valid fully qualified domain name.") from None
    labels = name.split(".")
    if (len(name) > 253 or len(labels) < 2 or any(
        not 1 <= len(label) <= 63
        or not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]*[a-z0-9])?", label)
        for label in labels
    )):
        raise CLIError("Supply a valid fully qualified domain name.")
    return name


def _read_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError):
        raise CLIError("Cannot read a valid JSON document from the supplied file.") from None
    if not isinstance(value, dict):
        raise CLIError("The JSON file must contain an object.")
    return value


def _credentials() -> CCPCredentials:
    return load_ccp_credentials() or CCPCredentials()


def _legacy() -> LegacyDnsClient:
    credentials = _credentials()
    if not all((credentials.customer_number, credentials.legacy_api_key, credentials.legacy_api_password)):
        raise CLIError("Legacy DNS needs NETCUP_CCP_CUSTOMER_NUMBER, NETCUP_CCP_LEGACY_API_KEY and NETCUP_CCP_LEGACY_API_PASSWORD, or 'dns auth set legacy'.")
    return LegacyDnsClient(credentials)


def _rest(*, public: bool = False) -> NetcupDnsApiClient:
    if public:
        return NetcupDnsApiClient("")
    key = _credentials().rest_api_key
    if not key:
        raise CLIError("CloudDNS REST needs NETCUP_API_KEY or 'dns auth set rest'.")
    return NetcupDnsApiClient(key)


def _cloud_domain(client: NetcupDnsApiClient, fqdn: str) -> tuple[int, str]:
    name = _fqdn(fqdn)
    domain = client.get_domain(name)
    if not domain["isDnsManaged"]:
        raise CLIError(f"{name} is not CloudDNS-managed according to the REST API. Legacy DNS eligibility is unverified; check the domain's DNS backend before using Legacy commands.")
    return domain["id"], name


def _confirm(message: str, *, yes: bool) -> None:
    confirm_action(f"{message} DNS changes can interrupt services.", yes=yes)


def _secret(prompt: str, environment: str) -> str:
    if not sys.stdin.isatty():
        raise CLIError(f"{prompt} requires an interactive prompt. Use {environment} for non-interactive API access.")
    entered = click.prompt(prompt, hide_input=True, confirmation_prompt=True)
    if not entered:
        raise CLIError(f"{prompt} cannot be empty.")
    return entered


def _safe_legacy_data(value: object, client: LegacyDnsClient) -> object:
    """Keep authentication material out of even an unexpected DNS response."""
    credentials = client._credentials
    secrets = tuple(item for item in (
        credentials.legacy_api_key, credentials.legacy_api_password, client._session_id,
    ) if item)
    hidden_keys = {"customernumber", "apikey", "apipassword", "apisessionid", "token", "authorization"}

    def scrub(item: object) -> object:
        if isinstance(item, dict):
            return {key: scrub(child) for key, child in item.items()
                    if str(key).lower() not in hidden_keys}
        if isinstance(item, list):
            return [scrub(child) for child in item]
        if isinstance(item, str):
            for secret in sorted(secrets, key=len, reverse=True):
                item = item.replace(secret, "[redacted]")
        return item

    return scrub(value)


@click.group("dns")
def dns_group() -> None:
    """Manage CCP DNS, CloudDNS REST and Dynamic DNS."""


@dns_group.group("auth")
def auth_group() -> None:
    """Configure CCP credentials separately from SCP login."""


@auth_group.command("show")
@click.pass_context
def auth_show(ctx: click.Context) -> None:
    """Show only which CCP credential groups are configured."""
    credentials = _credentials()
    _show(ctx, {
        "legacy": all((credentials.customer_number, credentials.legacy_api_key, credentials.legacy_api_password)),
        "rest": bool(credentials.rest_api_key),
        "ddns": bool(credentials.ddns_token),
    })


@auth_group.group("set")
def auth_set() -> None:
    """Save one CCP credential group (secrets are prompted privately)."""


@auth_set.command("legacy")
@click.option("--customer-number", help="CCP customer number; prompted when omitted.")
@click.option("--yes", "-y", is_flag=True, help="Confirm saving credentials.")
@click.pass_context
def auth_set_legacy(ctx: click.Context, customer_number: str | None, yes: bool) -> None:
    """Save customer number, Legacy API key and API password."""
    if not customer_number:
        if not sys.stdin.isatty():
            raise CLIError("Supply --customer-number interactively, or use NETCUP_CCP_CUSTOMER_NUMBER for non-interactive API access.")
        customer_number = click.prompt("CCP customer number")
    api_key = _secret("Legacy API key", "NETCUP_CCP_LEGACY_API_KEY")
    password = _secret("Legacy API password", "NETCUP_CCP_LEGACY_API_PASSWORD")
    confirm_action("Save Legacy DNS credentials?", yes=yes)
    credentials = load_stored_ccp_credentials() or CCPCredentials()
    credentials.customer_number = customer_number
    credentials.legacy_api_key = api_key
    credentials.legacy_api_password = password
    save_ccp_credentials(credentials)
    _show(ctx, {"legacy": True})


@auth_set.command("rest")
@click.option("--yes", "-y", is_flag=True, help="Confirm saving credentials.")
@click.pass_context
def auth_set_rest(ctx: click.Context, yes: bool) -> None:
    """Save the CloudDNS REST API key."""
    key = _secret("REST API key", "NETCUP_API_KEY")
    confirm_action("Save REST API credentials?", yes=yes)
    credentials = load_stored_ccp_credentials() or CCPCredentials()
    credentials.rest_api_key = key
    save_ccp_credentials(credentials)
    _show(ctx, {"rest": True})


@auth_set.command("ddns")
@click.option("--yes", "-y", is_flag=True, help="Confirm saving credentials.")
@click.pass_context
def auth_set_ddns(ctx: click.Context, yes: bool) -> None:
    """Save the CloudDNS Dynamic DNS token."""
    token = _secret("DynDNS token", "NETCUP_DDNS_TOKEN")
    confirm_action("Save DynDNS credentials?", yes=yes)
    credentials = load_stored_ccp_credentials() or CCPCredentials()
    credentials.ddns_token = token
    save_ccp_credentials(credentials)
    _show(ctx, {"ddns": True})


@auth_group.command("clear")
@click.argument("scope", type=click.Choice(["legacy", "rest", "ddns", "all"]))
@click.option("--yes", "-y", is_flag=True)
@click.pass_context
def auth_clear(ctx: click.Context, scope: str, yes: bool) -> None:
    """Remove saved CCP credentials in one scope; environment values remain."""
    confirm_action(f"Clear saved {scope} credentials?", yes=yes)
    if scope == "all":
        delete_ccp_credentials()
    else:
        credentials = load_stored_ccp_credentials() or CCPCredentials()
        if scope == "legacy":
            credentials.customer_number = None
            credentials.legacy_api_key = None
            credentials.legacy_api_password = None
        elif scope == "rest":
            credentials.rest_api_key = None
        else:
            credentials.ddns_token = None
        save_ccp_credentials(credentials)
    _show(ctx, {"cleared": scope})


@dns_group.group("domains")
def domains_group() -> None:
    """Look up one supplied domain through CloudDNS REST."""


@domains_group.command("get")
@click.argument("fqdn")
@click.pass_context
def domain_get(ctx: click.Context, fqdn: str) -> None:
    """Get a domain and its CloudDNS status; Legacy eligibility is unverified."""
    domain = _rest().get_domain(_fqdn(fqdn))
    _show(ctx, {**domain, "dnsBackend": "CloudDNS" if domain["isDnsManaged"] else "not CloudDNS; Legacy eligibility unverified"})


@dns_group.group("record-types")
def record_types_group() -> None:
    """Inspect public REST DNS record types."""


@record_types_group.command("list")
@click.pass_context
def record_types_list(ctx: click.Context) -> None:
    """List supported record types; no API key is needed."""
    _show(ctx, _rest(public=True).list_record_types())


@dns_group.group("zone")
def zone_group() -> None:
    """Read or update classic DNS zone settings through Legacy CCP."""


@zone_group.command("get")
@click.argument("domain")
@click.pass_context
def zone_get(ctx: click.Context, domain: str) -> None:
    """Read a classic DNS zone."""
    client = _legacy()
    with client.session():
        result = client.call("infoDnsZone", {"domainname": _fqdn(domain)})
        data = _safe_legacy_data(result.get("responsedata"), client)
    _show(ctx, data)


@zone_group.command("update")
@click.argument("domain")
@click.option("--file", "body_file", type=click.Path(path_type=Path, exists=True, dir_okay=False), required=True, help="JSON object for dnszone.")
@click.option("--yes", "-y", is_flag=True)
@click.pass_context
def zone_update(ctx: click.Context, domain: str, body_file: Path, yes: bool) -> None:
    """Update classic DNS zone settings from a JSON object."""
    name, body = _fqdn(domain), _read_object(body_file)
    _confirm(f"Update the classic DNS zone for {name}?", yes=yes)
    client = _legacy()
    with client.session():
        result = client.call("updateDnsZone", {"domainname": name, "dnszone": body})
        data = _safe_legacy_data(result.get("responsedata"), client)
    _show(ctx, data)


@dns_group.group("records")
def records_group() -> None:
    """Read or update classic DNS records through Legacy CCP."""


@records_group.command("list")
@click.argument("domain")
@click.pass_context
def records_list(ctx: click.Context, domain: str) -> None:
    """Read records of a classic DNS domain."""
    client = _legacy()
    with client.session():
        result = client.call("infoDnsRecords", {"domainname": _fqdn(domain)})
        data = _safe_legacy_data(result.get("responsedata"), client)
    _show(ctx, data)


@records_group.command("update")
@click.argument("domain")
@click.option("--file", "body_file", type=click.Path(path_type=Path, exists=True, dir_okay=False), required=True, help="JSON object for dnsrecordset.")
@click.option("--yes", "-y", is_flag=True)
@click.pass_context
def records_update(ctx: click.Context, domain: str, body_file: Path, yes: bool) -> None:
    """Update classic DNS records from a JSON object."""
    name, body = _fqdn(domain), _read_object(body_file)
    _confirm(f"Update classic DNS records for {name}?", yes=yes)
    client = _legacy()
    with client.session():
        result = client.call("updateDnsRecords", {"domainname": name, "dnsrecordset": body})
        data = _safe_legacy_data(result.get("responsedata"), client)
    _show(ctx, data)


@dns_group.group("acme")
def acme_group() -> None:
    """Manage CloudDNS ACME challenge records via REST."""


@acme_group.command("list")
@click.argument("fqdn")
@click.pass_context
def acme_list(ctx: click.Context, fqdn: str) -> None:
    """List ACME challenges."""
    client = _rest()
    domain_id, _ = _cloud_domain(client, fqdn)
    _show(ctx, client.list_acme_challenges(domain_id))


@acme_group.command("add")
@click.argument("fqdn")
@click.argument("scope")
@click.argument("value")
@click.option("--yes", "-y", is_flag=True)
@click.pass_context
def acme_add(ctx: click.Context, fqdn: str, scope: str, value: str, yes: bool) -> None:
    """Create an ACME challenge (43-character base64url value)."""
    _confirm(f"Create an ACME challenge for {_fqdn(fqdn)}?", yes=yes)
    client = _rest()
    domain_id, _ = _cloud_domain(client, fqdn)
    _show(ctx, client.create_acme_challenge(domain_id, scope, value))


@acme_group.command("get")
@click.argument("fqdn")
@click.argument("scope")
@click.argument("value")
@click.pass_context
def acme_get(ctx: click.Context, fqdn: str, scope: str, value: str) -> None:
    """Get one ACME challenge."""
    client = _rest()
    domain_id, _ = _cloud_domain(client, fqdn)
    _show(ctx, client.get_acme_challenge(domain_id, scope, value))


@acme_group.command("delete")
@click.argument("fqdn")
@click.argument("scope")
@click.argument("value")
@click.option("--yes", "-y", is_flag=True)
@click.pass_context
def acme_delete(ctx: click.Context, fqdn: str, scope: str, value: str, yes: bool) -> None:
    """Delete one ACME challenge."""
    _confirm(f"Delete an ACME challenge for {_fqdn(fqdn)}?", yes=yes)
    client = _rest()
    domain_id, _ = _cloud_domain(client, fqdn)
    _show(ctx, client.delete_acme_challenge(domain_id, scope, value))


@dns_group.group("changeset")
def changeset_group() -> None:
    """Apply CloudDNS record changesets via REST."""


@changeset_group.command("apply")
@click.argument("fqdn")
@click.option("--file", "body_file", type=click.Path(path_type=Path, exists=True, dir_okay=False), required=True, help="JSON object with autoCommit, strict, create and/or delete.")
@click.option("--yes", "-y", is_flag=True)
@click.pass_context
def changeset_apply(ctx: click.Context, fqdn: str, body_file: Path, yes: bool) -> None:
    """Apply a CloudDNS changeset from a JSON file."""
    body = _read_object(body_file)
    _confirm(f"Apply a CloudDNS changeset for {_fqdn(fqdn)}?", yes=yes)
    client = _rest()
    domain_id, _ = _cloud_domain(client, fqdn)
    _show(ctx, client.apply_changeset(domain_id, body))


@dns_group.group("revisions")
def revisions_group() -> None:
    """Manage CloudDNS revisions via REST."""


@revisions_group.command("list")
@click.argument("fqdn")
@click.option("--field", type=str, help="Sort field accepted by the REST API.")
@click.option("--direction", type=click.Choice(["asc", "desc"]))
@click.option("--page", type=click.IntRange(min=1))
@click.option("--per-page", type=click.IntRange(min=1))
@click.pass_context
def revisions_list(ctx: click.Context, fqdn: str, field: str | None, direction: str | None,
                   page: int | None, per_page: int | None) -> None:
    """List CloudDNS revisions with optional paging and sort."""
    client = _rest()
    domain_id, _ = _cloud_domain(client, fqdn)
    _show(ctx, client.list_revisions(domain_id, field=field, direction=direction, page=page, per_page=per_page))


@revisions_group.command("create")
@click.argument("fqdn")
@click.option("--yes", "-y", is_flag=True)
@click.pass_context
def revisions_create(ctx: click.Context, fqdn: str, yes: bool) -> None:
    """Create a CloudDNS revision."""
    _confirm(f"Create a CloudDNS revision for {_fqdn(fqdn)}?", yes=yes)
    client = _rest()
    domain_id, _ = _cloud_domain(client, fqdn)
    _show(ctx, client.create_revision(domain_id))


@revisions_group.command("get")
@click.argument("fqdn")
@click.argument("revision_id")
@click.pass_context
def revisions_get(ctx: click.Context, fqdn: str, revision_id: str) -> None:
    """Get one CloudDNS revision by UUID."""
    client = _rest()
    domain_id, _ = _cloud_domain(client, fqdn)
    _show(ctx, client.get_revision(domain_id, revision_id))


@revisions_group.command("delete")
@click.argument("fqdn")
@click.argument("revision_id")
@click.option("--yes", "-y", is_flag=True)
@click.pass_context
def revisions_delete(ctx: click.Context, fqdn: str, revision_id: str, yes: bool) -> None:
    """Delete one CloudDNS revision."""
    _confirm(f"Delete revision {revision_id} for {_fqdn(fqdn)}?", yes=yes)
    client = _rest()
    domain_id, _ = _cloud_domain(client, fqdn)
    _show(ctx, client.delete_revision(domain_id, revision_id))


@revisions_group.group("changeset")
def revision_changeset_group() -> None:
    """Apply a changeset to a specific revision."""


@revision_changeset_group.command("apply")
@click.argument("fqdn")
@click.argument("revision_id")
@click.option("--file", "body_file", type=click.Path(path_type=Path, exists=True, dir_okay=False), required=True)
@click.option("--yes", "-y", is_flag=True)
@click.pass_context
def revision_changeset_apply(ctx: click.Context, fqdn: str, revision_id: str, body_file: Path, yes: bool) -> None:
    """Apply a JSON changeset to a CloudDNS revision."""
    body = _read_object(body_file)
    _confirm(f"Apply a changeset to revision {revision_id} for {_fqdn(fqdn)}?", yes=yes)
    client = _rest()
    domain_id, _ = _cloud_domain(client, fqdn)
    _show(ctx, client.apply_revision_changeset(domain_id, revision_id, body))


@revisions_group.command("commit")
@click.argument("fqdn")
@click.argument("revision_id")
@click.option("--yes", "-y", is_flag=True)
@click.pass_context
def revisions_commit(ctx: click.Context, fqdn: str, revision_id: str, yes: bool) -> None:
    """Commit a CloudDNS revision."""
    _confirm(f"Commit revision {revision_id} for {_fqdn(fqdn)}?", yes=yes)
    client = _rest()
    domain_id, _ = _cloud_domain(client, fqdn)
    _show(ctx, client.commit_revision(domain_id, revision_id))


@revisions_group.group("records")
def revision_records_group() -> None:
    """Manage records within a CloudDNS revision."""


@revision_records_group.command("list")
@click.argument("fqdn")
@click.argument("revision_id")
@click.pass_context
def revision_records_list(ctx: click.Context, fqdn: str, revision_id: str) -> None:
    """List records in one revision."""
    client = _rest()
    domain_id, _ = _cloud_domain(client, fqdn)
    _show(ctx, client.list_revision_records(domain_id, revision_id))


@revision_records_group.command("add")
@click.argument("fqdn")
@click.argument("revision_id")
@click.option("--file", "body_file", type=click.Path(path_type=Path, exists=True, dir_okay=False), required=True, help="JSON object with name, type, rdata and ttl.")
@click.option("--yes", "-y", is_flag=True)
@click.pass_context
def revision_records_add(ctx: click.Context, fqdn: str, revision_id: str, body_file: Path, yes: bool) -> None:
    """Add one record to a CloudDNS revision."""
    body = _read_object(body_file)
    _confirm(f"Add a record to revision {revision_id} for {_fqdn(fqdn)}?", yes=yes)
    client = _rest()
    domain_id, _ = _cloud_domain(client, fqdn)
    _show(ctx, client.create_revision_record(domain_id, revision_id, body))


@revision_records_group.command("get")
@click.argument("fqdn")
@click.argument("revision_id")
@click.argument("record_id")
@click.pass_context
def revision_records_get(ctx: click.Context, fqdn: str, revision_id: str, record_id: str) -> None:
    """Get one record by UUID."""
    client = _rest()
    domain_id, _ = _cloud_domain(client, fqdn)
    _show(ctx, client.get_revision_record(domain_id, revision_id, record_id))


@revision_records_group.command("delete")
@click.argument("fqdn")
@click.argument("revision_id")
@click.argument("record_id")
@click.option("--yes", "-y", is_flag=True)
@click.pass_context
def revision_records_delete(ctx: click.Context, fqdn: str, revision_id: str, record_id: str, yes: bool) -> None:
    """Delete one record from a CloudDNS revision."""
    _confirm(f"Delete record {record_id} from revision {revision_id} for {_fqdn(fqdn)}?", yes=yes)
    client = _rest()
    domain_id, _ = _cloud_domain(client, fqdn)
    _show(ctx, client.delete_revision_record(domain_id, revision_id, record_id))


@dns_group.group("ddns")
def ddns_group() -> None:
    """Update CloudDNS A and AAAA records with a DynDNS token."""


@ddns_group.command("update")
@click.argument("fqdn")
@click.option("--ipv4", help="IPv4 address for the A record.")
@click.option("--ipv6", help="IPv6 address for the AAAA record.")
@click.option("--yes", "-y", is_flag=True)
@click.pass_context
def ddns_update(ctx: click.Context, fqdn: str, ipv4: str | None, ipv6: str | None, yes: bool) -> None:
    """Update one or both IP families for a CloudDNS FQDN."""
    if ipv4 is None and ipv6 is None:
        raise CLIError("Supply --ipv4, --ipv6, or both.")
    name = _fqdn(fqdn)
    token = _credentials().ddns_token
    if not token:
        raise CLIError("CloudDNS DynDNS needs NETCUP_DDNS_TOKEN or 'dns auth set ddns'.")
    _confirm(f"Update A and/or AAAA records for {name}?", yes=yes)
    _show(ctx, update_ddns(token, name, ipv4=ipv4, ipv6=ipv6))
