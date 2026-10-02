from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

import requests

from netcup_cli.auth import AuthClient, TokenSet
from netcup_cli.config import SCP_BASE, load_credentials, save_credentials, Credentials
from netcup_cli.errors import CLIError, api_error

_API_PREFIX = "/api/v1"
_TIMEOUT = 30


@dataclass
class SCPClient:
    access_token: str

    @property
    def user_id(self) -> str:
        import base64
        import json as _json
        payload = self.access_token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        claims = _json.loads(base64.urlsafe_b64decode(payload))
        if "id" not in claims:
            raise CLIError("Access token has no user id claim.")
        return str(claims["id"])

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/json, text/plain;q=0.5",
            "Content-Type": "application/json",
        }

    def request(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, object] | None = None,
        json_body: object | None = None,
        merge_patch: bool = False,
    ) -> object | None:
        import json as _json
        if path == "/users/me" or path.startswith("/users/me/"):
            path = f"/users/{self.user_id}{path[len('/users/me'):]}"
        url = f"{SCP_BASE}{path}" if path.startswith("/api/") else f"{SCP_BASE}{_API_PREFIX}{path}"
        headers = self._headers()
        if merge_patch:
            headers["Content-Type"] = "application/merge-patch+json"
        try:
            resp = requests.request(
                method.upper(),
                url,
                headers=headers,
                params=params,
                data=_json.dumps(json_body) if merge_patch and json_body is not None else None,
                json=json_body if not merge_patch else None,
                timeout=_TIMEOUT,
            )
        except requests.Timeout:
            raise CLIError(f"{method.upper()} {path} timed out after {_TIMEOUT}s.")
        except requests.ConnectionError as exc:
            raise CLIError(f"Connection error for {method.upper()} {path}: {exc}") from exc

        if resp.status_code == 401:
            raise CLIError("Authentication failed. Run 'netcup-cli login' to re-authenticate.")
        if resp.status_code == 403:
            raise CLIError(f"Permission denied for {method.upper()} {path}.")
        if resp.status_code == 429:
            raise CLIError(f"Rate limited on {method.upper()} {path}. Try again later.")
        if not resp.ok:
            raise api_error(resp, f"{method.upper()} {path}")

        if resp.status_code == 204 or not resp.content:
            return None
        if resp.headers.get("Content-Type", "").startswith("text/plain"):
            return resp.text.strip()
        try:
            return resp.json()
        except Exception:
            raise CLIError(f"Non-JSON response from {method.upper()} {path}: {resp.text[:200]}")

    def upload_presigned(
        self,
        url: str,
        file_path: Path,
        *,
        headers: Mapping[str, str] | None = None,
    ) -> str | None:
        hdrs = dict(headers or {})
        hdrs.pop("Authorization", None)
        with open(file_path, "rb") as fh:
            resp = requests.put(url, data=fh, headers=hdrs, timeout=300)
        if not resp.ok:
            raise CLIError(f"Presigned upload failed ({resp.status_code}): {resp.text[:200]}")
        return resp.headers.get("ETag")


def resolve_server(client: SCPClient, name: str) -> str:
    """Resolve numeric ID, nickname, hostname, or internal name (v22...) to a server ID."""
    if str(name).isdigit():
        return str(name)
    servers = client.request("GET", "/servers")
    items = servers if isinstance(servers, list) else []
    for s in items:
        if name in (s.get("nickname"), s.get("hostname"), s.get("name"), str(s.get("id"))):
            return str(s["id"])
    raise CLIError(f"No server found for '{name}'. Use 'netcup-cli list' to see available servers.")


def build_client() -> SCPClient:
    creds = load_credentials()
    if creds is None:
        raise CLIError("Not logged in. Run 'netcup-cli login' first.")
    auth = AuthClient()
    token_set: TokenSet = auth.refresh(creds.refresh_token)
    if token_set.refresh_token and token_set.refresh_token != creds.refresh_token:
        save_credentials(Credentials(refresh_token=token_set.refresh_token))
    return SCPClient(access_token=token_set.access_token)
