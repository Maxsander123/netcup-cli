from __future__ import annotations

import sys
import time
from dataclasses import dataclass

import requests

from netcup_cli.config import DISCOVERY_URL, OIDC_CLIENT_ID
from netcup_cli.errors import CLIError


@dataclass
class TokenSet:
    access_token: str
    refresh_token: str | None = None


class AuthClient:
    def __init__(self) -> None:
        self._discovery: dict | None = None

    def _get_discovery(self) -> dict:
        if self._discovery is None:
            try:
                resp = requests.get(DISCOVERY_URL, timeout=15)
                resp.raise_for_status()
                self._discovery = resp.json()
            except Exception as exc:
                raise CLIError(f"OIDC discovery failed: {exc}") from exc
        return self._discovery

    def login_device(self) -> TokenSet:
        disc = self._get_discovery()
        device_ep = disc.get("device_authorization_endpoint")
        token_ep = disc["token_endpoint"]

        if not device_ep:
            raise CLIError("OIDC provider does not support device code flow.")

        resp = requests.post(
            device_ep,
            data={"client_id": OIDC_CLIENT_ID, "scope": "openid offline_access"},
            timeout=15,
        )
        if not resp.ok:
            raise CLIError(f"Device code request failed: {resp.text[:300]}")
        data = resp.json()

        uri = data.get("verification_uri_complete") or data.get("verification_uri", "")
        user_code = data.get("user_code", "")
        device_code = data["device_code"]
        interval = data.get("interval", 5)

        print(f"\nOpen this URL in your browser:\n  {uri}")
        if user_code and "verification_uri_complete" not in data:
            print(f"  User code: {user_code}")
        print()

        sys.stdout.write("Waiting for browser authentication")
        sys.stdout.flush()

        while True:
            time.sleep(interval)
            r = requests.post(
                token_ep,
                data={
                    "client_id": OIDC_CLIENT_ID,
                    "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                    "device_code": device_code,
                },
                timeout=15,
            )
            tok = r.json()
            if r.ok:
                sys.stdout.write("\n")
                sys.stdout.flush()
                refresh = tok.get("refresh_token")
                if not refresh:
                    raise CLIError(
                        "Login succeeded but no refresh token returned. "
                        "Ensure the 'offline_access' scope is enabled."
                    )
                return TokenSet(access_token=tok["access_token"], refresh_token=refresh)
            err = tok.get("error", "")
            if err == "authorization_pending":
                sys.stdout.write(".")
                sys.stdout.flush()
            elif err == "slow_down":
                interval += 5
            elif err in ("access_denied", "expired_token"):
                sys.stdout.write("\n")
                raise CLIError(
                    f"Login {err.replace('_', ' ')}: run 'netcup-cli auth login' to try again."
                )
            else:
                sys.stdout.write("\n")
                raise CLIError(
                    f"Login failed ({err}): {tok.get('error_description', '')}. "
                    "Run 'netcup-cli auth login' to try again."
                )

    def refresh(self, refresh_token: str) -> TokenSet:
        disc = self._get_discovery()
        token_ep = disc["token_endpoint"]
        resp = requests.post(
            token_ep,
            data={
                "client_id": OIDC_CLIENT_ID,
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
            },
            timeout=15,
        )
        if not resp.ok:
            try:
                msg = resp.json().get("error_description", str(resp.status_code))
            except Exception:
                msg = str(resp.status_code)
            raise CLIError(
                f"Token refresh failed ({msg}). Run 'netcup-cli auth login' to re-authenticate."
            )
        tok = resp.json()
        return TokenSet(
            access_token=tok["access_token"],
            refresh_token=tok.get("refresh_token"),
        )

    def revoke(self, refresh_token: str) -> None:
        disc = self._get_discovery()
        revoke_ep = disc.get("revocation_endpoint")
        if not revoke_ep:
            return
        requests.post(
            revoke_ep,
            data={
                "client_id": OIDC_CLIENT_ID,
                "token": refresh_token,
                "token_type_hint": "refresh_token",
            },
            timeout=15,
        )
