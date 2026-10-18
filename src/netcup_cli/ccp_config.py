"""Independent credentials for the Netcup Customer Control Panel DNS APIs.

``load_ccp_credentials`` applies environment overrides for API use. Commands
that edit saved settings should start with ``load_stored_ccp_credentials`` so
environment-only secrets are not copied into the credentials file.
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from netcup_cli.config import CONFIG_DIR
from netcup_cli.errors import CLIError

_CCP_CREDS_FILE = CONFIG_DIR / "ccp-credentials.json"
_ENV_NAMES = {
    "customer_number": "NETCUP_CCP_CUSTOMER_NUMBER",
    "legacy_api_key": "NETCUP_CCP_LEGACY_API_KEY",
    "legacy_api_password": "NETCUP_CCP_LEGACY_API_PASSWORD",
    "rest_api_key": "NETCUP_API_KEY",
    "ddns_token": "NETCUP_DDNS_TOKEN",
}


@dataclass(repr=False)
class CCPCredentials:
    customer_number: str | None = field(default=None, repr=False)
    legacy_api_key: str | None = field(default=None, repr=False)
    legacy_api_password: str | None = field(default=None, repr=False)
    rest_api_key: str | None = field(default=None, repr=False)
    ddns_token: str | None = field(default=None, repr=False)

    def to_dict(self) -> dict[str, str | None]:
        """Return values for explicit storage; never use this for CLI output."""
        return {name: getattr(self, name) for name in _ENV_NAMES}


def load_stored_ccp_credentials() -> CCPCredentials | None:
    """Read saved CCP settings without applying environment overrides."""
    try:
        data = json.loads(_CCP_CREDS_FILE.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except json.JSONDecodeError:
        raise CLIError("CCP credentials file is malformed.") from None
    except (OSError, UnicodeError):
        raise CLIError("Cannot read CCP credentials file.") from None

    if not isinstance(data, dict) or any(
        name not in _ENV_NAMES or (value is not None and not isinstance(value, str))
        for name, value in data.items()
    ):
        raise CLIError("CCP credentials file is malformed.")

    credentials = CCPCredentials(**data)
    return credentials if any(credentials.to_dict().values()) else None


def load_ccp_credentials() -> CCPCredentials | None:
    """Load saved CCP settings with nonempty environment values taking priority."""
    stored = load_stored_ccp_credentials()
    values = stored.to_dict() if stored is not None else {}
    for name, environment_name in _ENV_NAMES.items():
        if value := os.environ.get(environment_name):
            values[name] = value
    credentials = CCPCredentials(**values)
    return credentials if any(credentials.to_dict().values()) else None


def save_ccp_credentials(credentials: CCPCredentials) -> None:
    """Atomically save explicitly supplied settings in a mode-0600 file."""
    if not isinstance(credentials, CCPCredentials):
        raise TypeError("Expected CCPCredentials")
    values = credentials.to_dict()
    if any(value is not None and not isinstance(value, str) for value in values.values()):
        raise ValueError("CCP credential fields must be strings or None")

    CONFIG_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix=".ccp-credentials-", suffix=".tmp", dir=CONFIG_DIR)
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            os.fchmod(stream.fileno(), 0o600)
            json.dump(values, stream, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        temporary_path.replace(_CCP_CREDS_FILE)
    finally:
        temporary_path.unlink(missing_ok=True)


def delete_ccp_credentials() -> None:
    """Remove saved CCP credentials without changing SCP credentials."""
    _CCP_CREDS_FILE.unlink(missing_ok=True)
