#!/usr/bin/env bash
# install-netcup-cli.sh — Install netcup-cli into a user-owned virtual environment.
set -euo pipefail

INSTALL_DIR="${NETCUP_CLI_INSTALL_DIR:-$HOME/.local/netcup-cli}"
BIN_DIR="${NETCUP_CLI_BIN_DIR:-$HOME/.local/bin}"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "Installing netcup-cli to $INSTALL_DIR ..."
python3 -m venv "$INSTALL_DIR"
"$INSTALL_DIR/bin/pip" install --quiet --upgrade pip
"$INSTALL_DIR/bin/pip" install --quiet "$REPO_DIR"

mkdir -p "$BIN_DIR"
cat > "$BIN_DIR/netcup-cli" <<EOF
#!/usr/bin/env bash
exec "$INSTALL_DIR/bin/netcup-cli" "\$@"
EOF
chmod +x "$BIN_DIR/netcup-cli"

echo "netcup-cli installed. Make sure $BIN_DIR is in your PATH."
echo "Run: netcup-cli login"
