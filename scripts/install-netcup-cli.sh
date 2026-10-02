#!/usr/bin/env bash
# install-netcup-cli.sh — Install netcup-cli via uv tool install.
# Works both from a local clone and via: curl -fsSL <url> | bash
set -euo pipefail

REPO="https://github.com/Maxsander123/netcup-cli"

if ! command -v uv &>/dev/null; then
    echo "uv not found. Install it first:"
    echo "  curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# If run from inside a local clone, install from there; otherwise pull from GitHub.
if [[ -n "${BASH_SOURCE[0]:-}" && "${BASH_SOURCE[0]}" != "/dev/stdin" ]]; then
    LOCAL="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
    echo "Installing netcup-cli from $LOCAL ..."
    uv tool install "$LOCAL" --force
else
    echo "Installing netcup-cli from GitHub ..."
    uv tool install "git+$REPO" --force
fi

echo ""
echo "✓ netcup-cli installed. Run: netcup-cli login"
