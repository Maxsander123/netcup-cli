"""Scoped client for the non-reseller Legacy CCP DNS JSON API."""

from __future__ import annotations

import sys
from contextlib import contextmanager
from typing import Iterator

import requests

from netcup_cli.ccp_config import CCPCredentials
from netcup_cli.errors import CLIError


_ENDPOINT = "https://ccp.netcup.net/run/webservice/servers/endpoint.php?JSON"
_TIMEOUT = 30
_DNS_ACTIONS = frozenset({"infoDnsZone", "infoDnsRecords", "updateDnsZone", "updateDnsRecords"})
_ACTIONS = _DNS_ACTIONS | {"login", "logout"}
_AUTH_KEYS = frozenset({"customernumber", "apikey", "apipassword", "apisessionid"})
_ACTION_PARAMS = {
    "infoDnsZone": frozenset({"domainname"}),
    "infoDnsRecords": frozenset({"domainname"}),
    "updateDnsZone": frozenset({"domainname", "dnszone"}),
    "updateDnsRecords": frozenset({"domainname", "dnsrecordset"}),
}


class LegacyDnsClient:
    """Keep one Legacy API session in memory for a scoped DNS operation."""

    def __init__(self, credentials: CCPCredentials) -> None:
        if not isinstance(credentials, CCPCredentials):
            raise TypeError("Expected CCPCredentials")
        self._credentials = credentials
        self._session_id: str | None = None

    def _safe_message(self, value: object, *, session_id: str | None = None) -> str:
        """Remove known credentials before including server feedback in an error."""
        if not isinstance(value, (str, int)) or isinstance(value, bool):
            return ""
        message = str(value)
        secrets = (
            self._credentials.customer_number,
            self._credentials.legacy_api_key,
            self._credentials.legacy_api_password,
            self._session_id,
            session_id,
        )
        for secret in sorted((item for item in secrets if item), key=len, reverse=True):
            message = message.replace(secret, "[redacted]")
        return message[:200].strip()

    def call(self, action: str, params: dict[str, object] | None = None) -> dict[str, object]:
        """Call one documented session or DNS action and check its API status."""
        if action not in _ACTIONS:
            raise CLIError("Unsupported Legacy DNS action.")
        if params is not None and not isinstance(params, dict):
            raise CLIError(f"{action} parameters must be a JSON object.")
        supplied = params or {}
        if _AUTH_KEYS.intersection(supplied):
            raise CLIError(f"{action} parameters must not contain authentication fields.")
        if action in _ACTION_PARAMS:
            missing = _ACTION_PARAMS[action] - supplied.keys()
            if missing:
                raise CLIError(f"{action} requires {', '.join(sorted(missing))}.")
        elif supplied:
            raise CLIError(f"{action} does not accept DNS parameters.")

        credentials = self._credentials
        if not credentials.customer_number or not credentials.legacy_api_key:
            raise CLIError("Legacy DNS requires a CCP customer number and Legacy API key.")

        auth: dict[str, object] = {
            "customernumber": credentials.customer_number,
            "apikey": credentials.legacy_api_key,
        }
        if action == "login":
            if self._session_id is not None:
                raise CLIError("Legacy DNS session is already active.")
            if not credentials.legacy_api_password:
                raise CLIError("Legacy DNS requires a Legacy API password.")
            auth["apipassword"] = credentials.legacy_api_password
        else:
            if self._session_id is None:
                raise CLIError("Legacy DNS session is not active.")
            auth["apisessionid"] = self._session_id

        payload = {"action": action, "param": {**auth, **supplied}}
        session_id = self._session_id
        try:
            response = requests.post(_ENDPOINT, json=payload, timeout=_TIMEOUT)
        except requests.Timeout:
            raise CLIError(f"Legacy DNS {action} timed out after {_TIMEOUT}s.") from None
        except requests.RequestException:
            raise CLIError(f"Could not connect to Legacy DNS API for {action}.") from None
        finally:
            if action == "logout":
                self._session_id = None

        if not response.ok:
            raise CLIError(f"Legacy DNS {action} failed (HTTP {response.status_code}).")
        try:
            result = response.json()
        except ValueError:
            raise CLIError(f"Legacy DNS {action} returned invalid JSON.") from None
        if not isinstance(result, dict):
            raise CLIError(f"Legacy DNS {action} returned an invalid response.")
        if result.get("status") != "success":
            code = self._safe_message(result.get("statuscode"), session_id=session_id)
            detail = self._safe_message(result.get("shortmessage"), session_id=session_id)
            suffix = f" (code {code})" if code else ""
            if detail:
                suffix += f": {detail}"
            raise CLIError(f"Legacy DNS {action} failed{suffix}.")

        if action == "login":
            data = result.get("responsedata")
            session_id = data.get("apisessionid") if isinstance(data, dict) else None
            if not isinstance(session_id, str) or not session_id:
                raise CLIError("Legacy DNS login returned no session ID.")
            self._session_id = session_id
        return result

    @contextmanager
    def session(self) -> Iterator[LegacyDnsClient]:
        """Login for command work and always attempt logout afterwards."""
        self.call("login")
        try:
            yield self
        finally:
            failed = sys.exc_info()[0] is not None
            try:
                self.call("logout")
            except CLIError:
                if not failed:
                    raise
