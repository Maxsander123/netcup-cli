"""CloudDNS Dynamic DNS updates via netcup's documented POST endpoint.

See https://www.netcup.com/en/helpcenter/documentation/domain/dyn-dns.
The request changes A and/or AAAA records for one FQDN. The token is sent in
the POST body so it does not appear in the request URL.
"""

from __future__ import annotations

import ipaddress
import re

import requests

from netcup_cli.errors import CLIError


_ENDPOINT = "https://customercontrolpanel.de/wsDynDns.php"
_TIMEOUT = 30
_SUCCESS_MESSAGES = frozenset({"Record(s) have been saved.", "No record update needed."})


def _fqdn(value: str) -> str:
    """Convert a complete host name to the ASCII form accepted by the API."""
    if not isinstance(value, str) or not value or value != value.strip():
        raise CLIError("Supply a valid fully qualified domain name.")
    name = value[:-1] if value.endswith(".") else value
    try:
        normalized = name.encode("idna").decode("ascii").lower()
    except UnicodeError:
        raise CLIError("Supply a valid fully qualified domain name.") from None
    labels = normalized.split(".")
    if (
        len(normalized) > 253
        or len(labels) < 2
        or any(
            not 1 <= len(label) <= 63
            or not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]*[a-z0-9])?", label)
            for label in labels
        )
    ):
        raise CLIError("Supply a valid fully qualified domain name.")
    return normalized


def _address(value: str, family: int) -> str:
    if not isinstance(value, str):
        raise CLIError(f"Supply a valid IPv{family} address.")
    try:
        address = ipaddress.ip_address(value)
    except ValueError:
        raise CLIError(f"Supply a valid IPv{family} address.") from None
    if address.version != family or getattr(address, "scope_id", None) is not None:
        raise CLIError(f"Supply a valid IPv{family} address.")
    return str(address)


def _api_error(status: int) -> CLIError:
    """Map documented HTTP failures without reflecting an untrusted body."""
    if status == 400:
        advice = "Check the FQDN and IP addresses, and confirm the domain uses CloudDNS."
    elif status == 401:
        advice = "Check the CloudDNS DynDNS token."
    elif status == 404:
        advice = "Check that the FQDN belongs to a domain in this account."
    elif status >= 500:
        advice = "Retry later or contact netcup support."
    else:
        advice = "Check the request and retry."
    return CLIError(f"CloudDNS DynDNS update failed (HTTP {status}). {advice}")


def update_ddns(
    token: str,
    fqdn: str,
    *,
    ipv4: str | None = None,
    ipv6: str | None = None,
) -> object:
    """Update one or both IP families in a single request.

    Returns a response with only the documented, non-sensitive status and
    message fields. The caller confirms a DNS mutation before invoking this.
    """
    if not isinstance(token, str) or not token.strip():
        raise CLIError("CloudDNS DynDNS requires a token.")
    if ipv4 is None and ipv6 is None:
        raise CLIError("Supply an IPv4 address, an IPv6 address, or both.")

    data = {"action": "update", "token": token, "fqdn": _fqdn(fqdn)}
    if ipv4 is not None:
        data["ipv4Address"] = _address(ipv4, 4)
    if ipv6 is not None:
        data["ipv6Address"] = _address(ipv6, 6)

    try:
        response = requests.post(_ENDPOINT, data=data, timeout=_TIMEOUT, allow_redirects=False)
    except requests.Timeout:
        raise CLIError(f"CloudDNS DynDNS update timed out after {_TIMEOUT}s.") from None
    except requests.RequestException:
        raise CLIError("Could not connect to the CloudDNS DynDNS API.") from None

    if not 200 <= response.status_code < 300:
        raise _api_error(response.status_code)
    try:
        result = response.json()
    except ValueError:
        raise CLIError("CloudDNS DynDNS returned invalid JSON.") from None
    if not isinstance(result, dict) or result.get("status") != "success":
        raise CLIError("CloudDNS DynDNS update failed. Check the FQDN, IP addresses, and token.")
    message = result.get("message")
    safe_message = message if isinstance(message, str) and message in _SUCCESS_MESSAGES else "DynDNS update accepted."
    return {"status": "success", "message": safe_message}
