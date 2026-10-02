#!/usr/bin/env bash
# install-netcup-cli.sh — Install netcup-cli into a user-owned virtual environment.
# Works both from a local clone and via: curl -fsSL <url> | bash
set -euo pipefail

REPO="https://github.com/Maxsander123/netcup-cli"
INSTALL_DIR="${NETCUP_CLI_INSTALL_DIR:-$HOME/.local/netcup-cli}"
BIN_DIR="${NETCUP_CLI_BIN_DIR:-$HOME/.local/bin}"

echo "Installing netcup-cli to $INSTALL_DIR ..."
python3 -m venv "$INSTALL_DIR"
"$INSTALL_DIR/bin/pip" install --quiet --upgrade pip

# If run from inside a local clone, install from there; otherwise pull from GitHub.
if [[ -n "${BASH_SOURCE[0]:-}" && "${BASH_SOURCE[0]}" != "/dev/stdin" ]]; then
    LOCAL="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
    "$INSTALL_DIR/bin/pip" install --quiet "$LOCAL"
else
    "$INSTALL_DIR/bin/pip" install --quiet "git+$REPO"
fi

mkdir -p "$BIN_DIR"
cat > "$BIN_DIR/netcup-cli" <<EOF
#!/usr/bin/env bash
exec "$INSTALL_DIR/bin/netcup-cli" "\$@"
EOF
chmod +x "$BIN_DIR/netcup-cli"

echo ""
echo "✓ netcup-cli installed."
echo "  Make sure $BIN_DIR is in your PATH, then run:"
echo "  netcup-cli login"
