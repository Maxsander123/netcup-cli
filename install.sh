#!/usr/bin/env bash
set -euo pipefail

VENV_DIR="$HOME/.local/lib/netbox-cli"
BIN_DIR="$HOME/.local/bin"
SCRIPT_SRC="$(cd "$(dirname "$0")" && pwd)/netbox-cli.py"

echo "[+] Creating venv at $VENV_DIR ..."
python3 -m venv "$VENV_DIR"

echo "[+] Installing dependencies ..."
"$VENV_DIR/bin/pip" install --quiet --upgrade pip
"$VENV_DIR/bin/pip" install --quiet click rich requests cryptography

echo "[+] Copying script ..."
cp "$SCRIPT_SRC" "$VENV_DIR/netbox-cli.py"
chmod 755 "$VENV_DIR/netbox-cli.py"

echo "[+] Writing shim to $BIN_DIR/netbox-cli ..."
mkdir -p "$BIN_DIR"
cat > "$BIN_DIR/netbox-cli" <<'SHIM'
#!/usr/bin/env bash
exec "$HOME/.local/lib/netbox-cli/bin/python3" \
     "$HOME/.local/lib/netbox-cli/netbox-cli.py" "$@"
SHIM
chmod 755 "$BIN_DIR/netbox-cli"

echo "[✓] Done. Make sure ~/.local/bin is in PATH, then run: netbox-cli login"
