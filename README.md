# netbox-cli

Standalone CLI zur Verwaltung von **Netcup VPS**-Servern.

---

## Installation

```bash
bash install.sh
```

Erstellt eine virtuelle Python-Umgebung unter `~/.local/share/netbox-cli/venv` und legt einen Shim unter `~/.local/bin/netbox-cli` an.

Abhängigkeiten: `click`, `requests`, `rich`

---

## Login

```bash
netbox-cli login
```

Öffnet den Browser automatisch (OAuth2 Device Code Flow mit `offline_access`-Scope). Nach einmaligem Login wird das `refresh_token` persistent in `~/.config/netbox-cli/netcup.json` (Modus 0600) gespeichert. Der `access_token` wird automatisch und lautlos erneuert — **kein erneuter Login nötig**.

```bash
netbox-cli logout
```

---

## Befehle

### Server

```bash
netbox-cli list [-f table|json|csv]
netbox-cli info <name|hostname|id>
netbox-cli info <name> --raw        # Rohe API-JSON-Ausgabe
```

### Power

```bash
netbox-cli start <name> [--force]
netbox-cli stop  <name> [--force]
netbox-cli reset <name> [--force]   # Hard-Reset / Reboot
```

### Traffic

```bash
netbox-cli traffic                  # Alle Server
netbox-cli traffic <name>           # Einzelner Server
netbox-cli traffic -f csv           # CSV-Export
```

### Snapshots

```bash
netbox-cli snapshot list   <name>
netbox-cli snapshot create <name> [--snap-name NAME] [--description TEXT]
netbox-cli snapshot delete <name> <snap_id> [--force]
netbox-cli snapshot restore <name> <snap_id> [--force]
```

---

## Shell-Completion

```bash
netbox-cli completion bash   # Anleitung für Bash
netbox-cli completion zsh    # Anleitung für Zsh
netbox-cli completion fish   # Anleitung für Fish
```

---

## Konfiguration

| Datei | Inhalt |
|-------|--------|
| `~/.config/netbox-cli/netcup.json` | Refresh-Token + Access-Token-Cache |

Alle Dateien werden mit Modus **0600** angelegt.
