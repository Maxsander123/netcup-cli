# netcup-cli

Command-line client for the [Netcup Server Control Panel (SCP) REST API](https://www.servercontrolpanel.de/).

## Installation

```bash
curl -fsSL https://raw.githubusercontent.com/Maxsander123/netcup-cli/main/scripts/install-netcup-cli.sh | bash
```

Requires [uv](https://astral.sh/uv) — if not installed yet:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## Quick start

```bash
netcup-cli login        # Browser-Login (kein Passwort)
netcup-cli list         # Alle Server
netcup-cli info 12345   # Server-Details
netcup-cli start 12345
netcup-cli stop 12345
netcup-cli reset 12345  # Hard-Reboot
```

## Snapshots

```bash
netcup-cli snapshot list 12345
netcup-cli snapshot create 12345 --name vor-update
netcup-cli snapshot restore 12345 <snap-id>
netcup-cli snapshot delete 12345 <snap-id>
```

## JSON-Ausgabe

```bash
netcup-cli --json list | jq '.[].hostname'
```

## Alle Befehle

| Befehl | Beschreibung |
|--------|-------------|
| `login` | Browser-Login (Device Code) |
| `logout` | Lokale Credentials löschen |
| `whoami` | Login-Status anzeigen |
| `list` | Alle Server auflisten |
| `info <id>` | Server-Details |
| `start <id>` | Server starten |
| `stop <id>` | Server stoppen |
| `reset <id>` | Hard-Reboot |
| `snapshot` | Snapshots verwalten |
| `rdns` | Reverse-DNS verwalten |
| `tasks` | Async-Tasks verwalten |
| `users` | User-Ressourcen |
| `servers` | Erweiterte Server-Ops (Disks, Interfaces, Metrics …) |

Weitere Infos: [docs/](docs/)
