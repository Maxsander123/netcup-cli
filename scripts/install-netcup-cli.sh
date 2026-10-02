#!/usr/bin/env bash
# install-netcup-cli.sh — Install netcup-cli via uv tool install.
# Works both from a local clone and via: curl -fsSL <url> | bash
set -euo pipefail

REPO="https://github.com/Maxsander123/netcup-cli"
MAN_DIR="${MANPATH:-$HOME/.local/share/man}/man1"

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
    # Install man page from local clone
    if [[ -f "$LOCAL/netcup-cli.1" ]]; then
        mkdir -p "$MAN_DIR"
        cp "$LOCAL/netcup-cli.1" "$MAN_DIR/netcup-cli.1"
        mandb -q 2>/dev/null || true
    fi
else
    echo "Installing netcup-cli from GitHub ..."
    uv tool install "git+$REPO" --force
    # Fetch and install man page
    if command -v curl &>/dev/null; then
        mkdir -p "$MAN_DIR"
        curl -fsSL "$REPO/raw/main/netcup-cli.1" -o "$MAN_DIR/netcup-cli.1" 2>/dev/null || true
        mandb -q 2>/dev/null || true
    fi
fi

echo ""
echo "✓ netcup-cli installed. Run: netcup-cli login"
echo "  Man page: man netcup-cli"
