from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

_xdg = os.environ.get("XDG_CONFIG_HOME")
CONFIG_DIR: Path = (Path(_xdg) if _xdg else Path.home() / ".config") / "netcup-cli"
_CREDS_FILE = CONFIG_DIR / "credentials.json"

OIDC_CLIENT_ID: str = os.environ.get("NETCUP_OIDC_CLIENT_ID", "scp")
DISCOVERY_URL = "https://www.servercontrolpanel.de/realms/scp/.well-known/openid-configuration"
SCP_BASE = "https://www.servercontrolpanel.de/scp-core"


@dataclass
class Credentials:
    refresh_token: str

    def to_dict(self) -> dict:
        return {"refresh_token": self.refresh_token}

    @staticmethod
    def from_dict(d: dict) -> "Credentials":
        return Credentials(refresh_token=d["refresh_token"])


def load_credentials() -> Credentials | None:
    if not _CREDS_FILE.exists():
        return None
    try:
        return Credentials.from_dict(json.loads(_CREDS_FILE.read_text()))
    except Exception:
        return None


def save_credentials(c: Credentials) -> None:
    CONFIG_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
    tmp = _CREDS_FILE.with_suffix(".tmp")
    fd = os.open(str(tmp), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        os.write(fd, json.dumps(c.to_dict(), indent=2).encode())
    finally:
        os.close(fd)
    tmp.replace(_CREDS_FILE)


def delete_credentials() -> None:
    if _CREDS_FILE.exists():
        _CREDS_FILE.unlink()
