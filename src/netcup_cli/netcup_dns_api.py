"""Named operations from ``docs/netcup-rest-openapi.json`` (2026.0921.153936).

The path in this mapping already contains ``/v1``. All methods except
``list_record_types`` use bearer authentication. Methods return the Netcup
response envelope; ``get_domain`` resolves one supplied FQDN to a domain.

Method/path mapping (``{d}``, ``{r}``, ``{i}`` mean domain, revision, record ID):

* ``GET /v1/dns/recordType``: ``list_record_types``
* ``GET /v1/domain``: ``list_domains`` (optional filters), ``get_domain``
  (filtered by ``fqdn``)
* ``GET, POST /v1/domain/{d}/acme/challenge``: ``list_acme_challenges``,
  ``create_acme_challenge``
* ``GET, DELETE /v1/domain/{d}/acme/challenge/{scope}/{value}``:
  ``get_acme_challenge``, ``delete_acme_challenge``
* ``POST /v1/domain/{d}/changeset``: ``apply_changeset``
* ``GET, POST /v1/domain/{d}/dns/revision``: ``list_revisions``,
  ``create_revision``
* ``GET, DELETE /v1/domain/{d}/dns/revision/{r}``: ``get_revision``,
  ``delete_revision``
* ``POST /v1/domain/{d}/dns/revision/{r}/changeset``:
  ``apply_revision_changeset``
* ``POST /v1/domain/{d}/dns/revision/{r}/commit``: ``commit_revision``
* ``GET, POST /v1/domain/{d}/dns/revision/{r}/record``:
  ``list_revision_records``, ``create_revision_record``
* ``GET, DELETE /v1/domain/{d}/dns/revision/{r}/record/{i}``:
  ``get_revision_record``, ``delete_revision_record``
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any
from urllib.parse import quote
from uuid import UUID

import requests

from netcup_cli.errors import CLIError


_BASE_URL = "https://api.netcup.com"
_TIMEOUT = 30
_ACME_VALUE = re.compile(r"[A-Za-z0-9_-]{43}\Z")
_RECORD_TYPES = frozenset(
    {"A", "AAAA", "CAA", "CNAME", "DS", "MX", "NS", "OPENPGPKEY", "SRV", "SMIMEA", "SSHFP", "TLSA", "TXT"}
)


def _fqdn(value: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise CLIError("Supply a valid domain name.")
    unqualified = value[:-1] if value.endswith(".") else value
    try:
        normalized = unqualified.encode("idna").decode("ascii").lower()
    except UnicodeError:
        raise CLIError("Supply a valid domain name.") from None
    labels = normalized.split(".")
    if (
        len(normalized) > 253
        or len(labels) < 2
        or any(not 1 <= len(label) <= 63 or not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]*[a-z0-9])?", label) for label in labels)
    ):
        raise CLIError("Supply a valid domain name.")
    return normalized


def _domain_id(value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise CLIError("Domain ID must be a positive integer.")
    return value


def _uuid(value: str, label: str) -> str:
    try:
        return str(UUID(value))
    except (ValueError, TypeError, AttributeError):
        raise CLIError(f"{label} must be a UUID.") from None


def _acme_parts(scope: str, value: str) -> tuple[str, str]:
    if not isinstance(scope, str) or not scope or (scope != "@" and not re.fullmatch(r"[A-Za-z0-9_-]+", scope)):
        raise CLIError("ACME scope must be @ or a hostname label.")
    if not isinstance(value, str) or not _ACME_VALUE.fullmatch(value):
        raise CLIError("ACME value must be 43 base64url characters.")
    return quote(scope, safe=""), quote(value, safe="")


def _record_body(body: Mapping[str, object]) -> dict[str, object]:
    if not isinstance(body, Mapping):
        raise CLIError("DNS record body must be a JSON object.")
    record = dict(body)
    for name in ("name", "type", "rdata"):
        if not isinstance(record.get(name), str):
            raise CLIError(f"DNS record requires a string {name}.")
    if len(record["name"]) > 255 or len(record["rdata"]) > 65535:
        raise CLIError("DNS record name or data exceeds the API length limit.")
    if record["type"] not in _RECORD_TYPES:
        raise CLIError("DNS record type is not supported by the Netcup REST API.")
    ttl = record.get("ttl")
    if isinstance(ttl, bool) or not isinstance(ttl, int) or ttl < 1:
        raise CLIError("DNS record ttl must be a positive integer.")
    return record


def _changeset_body(body: Mapping[str, object]) -> dict[str, object]:
    if not isinstance(body, Mapping):
        raise CLIError("DNS changeset body must be a JSON object.")
    result = dict(body)
    for name in ("autoCommit", "strict"):
        if not isinstance(result.get(name), bool):
            raise CLIError(f"DNS changeset requires a boolean {name}.")
    for name in ("create", "delete"):
        records = result.get(name)
        if records is not None:
            if not isinstance(records, list):
                raise CLIError(f"DNS changeset {name} must be an array or null.")
            result[name] = [_record_body(record) for record in records]
    return result


def _query(*, field: str | None = None, direction: str | None = None,
           page: int | None = None, per_page: int | None = None) -> dict[str, object]:
    if field is not None and not isinstance(field, str):
        raise CLIError("Sort field must be a string.")
    if direction is not None and direction not in ("asc", "desc"):
        raise CLIError("Sort direction must be asc or desc.")
    for label, value in (("page", page), ("perPage", per_page)):
        if value is not None and (isinstance(value, bool) or not isinstance(value, int) or value < 1):
            raise CLIError(f"{label} must be a positive integer.")
    return {key: value for key, value in
            (("field", field), ("direction", direction), ("page", page), ("perPage", per_page))
            if value is not None}


class NetcupDnsApiClient:
    """CloudDNS REST client with a private transport and explicit operations."""

    def __init__(self, api_key: str) -> None:
        if not isinstance(api_key, str):
            raise CLIError("Netcup REST DNS API key must be a string.")
        self._api_key = api_key

    @staticmethod
    def _error(operation: str, status: int, body: object) -> CLIError:
        """Use API codes when recognizable; never repeat server text or secrets."""
        codes: set[str] = set()
        if isinstance(body, dict) and isinstance(body.get("errors"), list):
            for item in body["errors"]:
                if isinstance(item, dict) and isinstance(item.get("code"), str):
                    codes.add(re.sub(r"[^a-z0-9]", "", item["code"].lower()))
        joined = " ".join(codes)
        if "auth" in joined or "apikey" in joined or status == 401:
            advice = "Check the Netcup REST API key."
        elif "permission" in joined or "forbidden" in joined or status == 403:
            advice = "Check API permissions and whether this domain uses CloudDNS."
        elif "notfound" in joined or status == 404:
            advice = "Check the domain, revision, or record identifier."
        elif "conflict" in joined or status == 409:
            advice = "Refresh the DNS revision and retry."
        elif "validation" in joined or "invalid" in joined or status in (400, 422):
            advice = "Check the request parameters and DNS record values."
        elif "ratelimit" in joined or status == 429:
            advice = "Wait before retrying."
        else:
            advice = "Retry later or check the Netcup API status."
        suffix = f" (HTTP {status})" if status else ""
        return CLIError(f"Netcup REST DNS {operation} failed{suffix}. {advice}")

    def _request(self, method: str, path: str, operation: str, *,
                 params: Mapping[str, object] | None = None,
                 body: Mapping[str, object] | None = None,
                 authenticated: bool = True) -> dict[str, Any] | None:
        headers = {"Accept": "application/json"}
        if authenticated:
            if not self._api_key.strip():
                raise CLIError("Netcup REST DNS requires an API key for this operation.")
            headers["Authorization"] = f"Bearer {self._api_key}"
        try:
            response = requests.request(
                method, f"{_BASE_URL}{path}", headers=headers,
                params=params, json=body, timeout=_TIMEOUT,
            )
        except requests.Timeout:
            raise CLIError(f"Netcup REST DNS {operation} timed out after {_TIMEOUT}s.") from None
        except requests.RequestException:
            raise CLIError(f"Could not connect to Netcup REST DNS for {operation}.") from None

        if response.status_code == 204 and response.ok:
            return None
        try:
            result = response.json()
        except ValueError:
            if not response.ok:
                raise self._error(operation, response.status_code, None) from None
            raise CLIError(f"Netcup REST DNS {operation} returned invalid JSON.") from None
        if not response.ok or not isinstance(result, dict) or result.get("success") is not True:
            raise self._error(operation, response.status_code, result)
        return result

    def list_record_types(self) -> dict[str, Any]:
        return self._request("GET", "/v1/dns/recordType", "record type list", authenticated=False)

    def list_domains(self, *, domain_id: int | None = None, fqdn: str | None = None,
                     field: str | None = None, direction: str | None = None,
                     page: int | None = None, per_page: int | None = None) -> dict[str, Any]:
        """List account domains using only supplied OpenAPI query parameters."""
        if field is not None and field not in ("domainId", "fqdn"):
            raise CLIError("Domain sort field must be domainId or fqdn.")
        params = _query(field=field, direction=direction, page=page, per_page=per_page)
        if domain_id is not None:
            params["domainId"] = _domain_id(domain_id)
        if fqdn is not None:
            params["fqdn"] = _fqdn(fqdn)
        response = self._request("GET", "/v1/domain", "domain list", params=params or None)
        if not isinstance(response, dict) or not isinstance(response.get("result"), list):
            raise CLIError("Netcup REST DNS domain list returned an invalid result.")
        return response

    def get_domain(self, fqdn: str) -> dict[str, Any]:
        """Resolve an exact, supplied FQDN via the filtered domain operation."""
        name = _fqdn(fqdn)
        response = self._request("GET", "/v1/domain", "domain lookup", params={"fqdn": name})
        domains = response.get("result") if response else None
        if not isinstance(domains, list):
            raise CLIError("Netcup REST DNS domain lookup returned an invalid result.")
        for domain in domains:
            if isinstance(domain, dict) and isinstance(domain.get("fqdn"), str):
                try:
                    domain_name = _fqdn(domain["fqdn"])
                except CLIError:
                    continue
                if domain_name == name:
                    if (isinstance(domain.get("id"), bool)
                            or not isinstance(domain.get("id"), int)
                            or domain["id"] < 1
                            or not isinstance(domain.get("isDnsManaged"), bool)):
                        raise CLIError("Netcup REST DNS domain lookup omitted its ID or DNS backend status.")
                    return domain
        raise CLIError("Domain was not found in this Netcup account. Check the FQDN and API key access.")

    def list_acme_challenges(self, domain_id: int) -> dict[str, Any]:
        return self._request("GET", f"/v1/domain/{_domain_id(domain_id)}/acme/challenge", "ACME challenge list")

    def create_acme_challenge(self, domain_id: int, scope: str, value: str) -> dict[str, Any]:
        _acme_parts(scope, value)
        return self._request("POST", f"/v1/domain/{_domain_id(domain_id)}/acme/challenge",
                             "ACME challenge creation", body={"scope": scope, "value": value})

    def get_acme_challenge(self, domain_id: int, scope: str, value: str) -> dict[str, Any]:
        scope_part, value_part = _acme_parts(scope, value)
        return self._request("GET", f"/v1/domain/{_domain_id(domain_id)}/acme/challenge/{scope_part}/{value_part}",
                             "ACME challenge lookup")

    def delete_acme_challenge(self, domain_id: int, scope: str, value: str) -> None:
        scope_part, value_part = _acme_parts(scope, value)
        self._request("DELETE", f"/v1/domain/{_domain_id(domain_id)}/acme/challenge/{scope_part}/{value_part}",
                      "ACME challenge deletion")

    def apply_changeset(self, domain_id: int, body: Mapping[str, object]) -> dict[str, Any]:
        return self._request("POST", f"/v1/domain/{_domain_id(domain_id)}/changeset",
                             "changeset apply", body=_changeset_body(body))

    def list_revisions(self, domain_id: int, *, field: str | None = None,
                       direction: str | None = None, page: int | None = None,
                       per_page: int | None = None) -> dict[str, Any]:
        return self._request("GET", f"/v1/domain/{_domain_id(domain_id)}/dns/revision",
                             "revision list", params=_query(field=field, direction=direction, page=page, per_page=per_page))

    def create_revision(self, domain_id: int) -> dict[str, Any]:
        return self._request("POST", f"/v1/domain/{_domain_id(domain_id)}/dns/revision", "revision creation")

    def get_revision(self, domain_id: int, revision_id: str) -> dict[str, Any]:
        return self._request("GET", f"/v1/domain/{_domain_id(domain_id)}/dns/revision/{_uuid(revision_id, 'Revision ID')}",
                             "revision lookup")

    def delete_revision(self, domain_id: int, revision_id: str) -> dict[str, Any]:
        return self._request("DELETE", f"/v1/domain/{_domain_id(domain_id)}/dns/revision/{_uuid(revision_id, 'Revision ID')}",
                             "revision deletion")

    def apply_revision_changeset(self, domain_id: int, revision_id: str,
                                 body: Mapping[str, object]) -> dict[str, Any]:
        path = f"/v1/domain/{_domain_id(domain_id)}/dns/revision/{_uuid(revision_id, 'Revision ID')}/changeset"
        return self._request("POST", path, "revision changeset apply", body=_changeset_body(body))

    def commit_revision(self, domain_id: int, revision_id: str) -> dict[str, Any]:
        path = f"/v1/domain/{_domain_id(domain_id)}/dns/revision/{_uuid(revision_id, 'Revision ID')}/commit"
        return self._request("POST", path, "revision commit")

    def list_revision_records(self, domain_id: int, revision_id: str) -> dict[str, Any]:
        path = f"/v1/domain/{_domain_id(domain_id)}/dns/revision/{_uuid(revision_id, 'Revision ID')}/record"
        return self._request("GET", path, "revision record list")

    def create_revision_record(self, domain_id: int, revision_id: str,
                               body: Mapping[str, object]) -> dict[str, Any]:
        path = f"/v1/domain/{_domain_id(domain_id)}/dns/revision/{_uuid(revision_id, 'Revision ID')}/record"
        return self._request("POST", path, "revision record creation", body=_record_body(body))

    def get_revision_record(self, domain_id: int, revision_id: str, record_id: str) -> dict[str, Any]:
        path = (f"/v1/domain/{_domain_id(domain_id)}/dns/revision/{_uuid(revision_id, 'Revision ID')}"
                f"/record/{_uuid(record_id, 'Record ID')}")
        return self._request("GET", path, "revision record lookup")

    def delete_revision_record(self, domain_id: int, revision_id: str, record_id: str) -> dict[str, Any]:
        path = (f"/v1/domain/{_domain_id(domain_id)}/dns/revision/{_uuid(revision_id, 'Revision ID')}"
                f"/record/{_uuid(record_id, 'Record ID')}")
        return self._request("DELETE", path, "revision record deletion")
