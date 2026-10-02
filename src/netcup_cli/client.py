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

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def request(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, object] | None = None,
        json_body: object | None = None,
    ) -> object | None:
        url = f"{SCP_BASE}{_API_PREFIX}{path}"
        try:
            resp = requests.request(
                method.upper(),
                url,
                headers=self._headers(),
                params=params,
                json=json_body,
                timeout=_TIMEOUT,
            )
        except requests.Timeout:
            raise CLIError(f"{method.upper()} {path} timed out after {_TIMEOUT}s.")
        except requests.ConnectionError as exc:
            raise CLIError(f"Connection error for {method.upper()} {path}: {exc}") from exc

        if resp.status_code == 401:
            raise CLIError("Authentication failed. Run 'netcup-cli auth login' to re-authenticate.")
        if resp.status_code == 403:
            raise CLIError(f"Permission denied for {method.upper()} {path}.")
        if resp.status_code == 429:
            raise CLIError(f"Rate limited on {method.upper()} {path}. Try again later.")
        if not resp.ok:
            raise api_error(resp, f"{method.upper()} {path}")

        if resp.status_code == 204 or not resp.content:
            return None
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


def build_client() -> SCPClient:
    creds = load_credentials()
    if creds is None:
        raise CLIError("Not logged in. Run 'netcup-cli auth login' first.")
    auth = AuthClient()
    token_set: TokenSet = auth.refresh(creds.refresh_token)
    if token_set.refresh_token and token_set.refresh_token != creds.refresh_token:
        save_credentials(Credentials(refresh_token=token_set.refresh_token))
    return SCPClient(access_token=token_set.access_token)
