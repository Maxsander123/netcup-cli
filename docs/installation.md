# Installation

## Requirements

- Linux or macOS with Python 3.10 or newer
- [`uv`](https://docs.astral.sh/uv/)

The installer uses `uv tool install` to create an isolated environment and put
the `netcup-cli` executable in `~/.local/bin`.

## Install from GitHub

Install `uv` first if needed:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Then install the latest `main` version:

```bash
curl -fsSL https://raw.githubusercontent.com/Maxsander123/netcup-cli/main/scripts/install-netcup-cli.sh | bash
```

The installer also installs the `netcup-cli` man page. If the shell cannot find
`netcup-cli`, add `~/.local/bin` to `PATH` and open a new shell. Check the
installation with:

```bash
netcup-cli --version
netcup-cli --help
```

## Update

Update an existing install from GitHub:

```bash
netcup-cli update
```

The installer command above also reinstalls the latest GitHub version.

## Install from a local checkout

```bash
git clone https://github.com/Maxsander123/netcup-cli.git
cd netcup-cli
uv tool install .
```

To replace the installed copy after changing the checkout, run `uv tool install
--force .` from the repository root. For development inside a virtual
environment, run:

```bash
uv sync
uv run netcup-cli --help
```

## First setup

SCP server access and CCP DNS access use separate credentials. Start with SCP
login if you use server commands:

```bash
netcup-cli login
netcup-cli whoami
netcup-cli list
```

`login` prints a URL and device code. Complete sign-in in a browser; no account
password is entered into the CLI. For DNS, configure only the API credential
group required by the commands you plan to use. See
[Authentication](authentication.md#ccp-dns-setup).
