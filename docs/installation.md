# Installation

## Requirements

- Python 3.10+
- pip

## Installer script

```bash
bash scripts/install-netcup-cli.sh
```

Installs into `~/.local/netcup-cli/` and creates `~/.local/bin/netcup-cli`. Ensure `~/.local/bin` is in your `PATH`.

## Manual install

```bash
pip install -e .
# or into a venv:
python3 -m venv .venv && .venv/bin/pip install -e .
```

## From GitHub

```bash
git clone https://github.com/Maxsander123/netcup-cli
cd netcup-cli
pip install -e .
```

## Environment overrides

| Variable | Default | Purpose |
|----------|---------|---------|
| `XDG_CONFIG_HOME` | `~/.config` | Config directory root |
| `NETCUP_OIDC_CLIENT_ID` | `scp` | OIDC client ID override |
