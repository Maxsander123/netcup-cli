# netbox-cli

Standalone CLI zum Verwalten von **NetBox** (DCIM/IPAM/Virtualisierung) und **Netcup VPS** – direkt aus dem Terminal.

---

## Installation

```bash
bash install.sh
```

Das Skript erstellt eine virtuelle Python-Umgebung unter `~/.local/share/netbox-cli/venv` und legt einen Shim unter `~/.local/bin/netbox-cli` an.

Abhängigkeiten: `click`, `requests`, `rich`, `urllib3`

---

## NetBox – Schnellstart

```bash
# Einmalig: URL + API-Token speichern
netbox-cli login

# Status prüfen
netbox-cli status

# Berechtigungen pro Endpunkt anzeigen
netbox-cli capabilities
```

Das Token wird persistent in `~/.config/netbox-cli/config.json` (Modus 0600) gespeichert und bei jedem Befehl automatisch geladen.

---

## Netcup – Schnellstart

```bash
# Einmalig: OAuth2 Browser-Login (öffnet automatisch den Browser)
netbox-cli netcup login
```

Der Login verwendet den **OAuth2 Device Code Flow** mit `offline_access`-Scope. Das gespeicherte `refresh_token` wird automatisch gegen neue `access_token`s getauscht – **kein erneuter Login nötig, solange das Refresh-Token gültig ist**.

Credentials werden persistent in `~/.config/netbox-cli/netcup.json` (Modus 0600) gespeichert.

```bash
# Ausloggen
netbox-cli netcup logout
```

---

## NetBox – Befehle

### Geräte
```bash
netbox-cli device list [--role ROLE] [--site SITE] [--rack RACK] [--status STATUS] [--owner OWNER]
netbox-cli device info <name|id>
netbox-cli device search <query>
netbox-cli device create --name NAME --type TYPE --role ROLE --site SITE [--rack RACK] [--owner OWNER]
netbox-cli device delete <name|id>
netbox-cli device set-owner <name|id> <owner>
netbox-cli device set-status <name|id> <status>
netbox-cli device interfaces <name|id>
```

### Virtuelle Maschinen
```bash
netbox-cli vm list [--cluster CLUSTER] [--role ROLE] [--status STATUS] [--owner OWNER]
netbox-cli vm info <name|id>
netbox-cli vm search <query>
netbox-cli vm create --name NAME --cluster CLUSTER [--vcpus N] [--ram MB] [--disk GB]
netbox-cli vm delete <name|id>
netbox-cli vm set-status <name|id> <status>
netbox-cli vm interfaces <name|id>
netbox-cli vm clusters
```

### Stromversorgung
```bash
netbox-cli power feeds [--rack RACK]
netbox-cli power panels
netbox-cli power ports <device>
netbox-cli power outlets <device>
```

### IP-Adressen
```bash
netbox-cli ip list [--device DEVICE] [--prefix PREFIX] [--free]
netbox-cli ip info <address>
netbox-cli ip create <address> [--dns-name NAME] [--status STATUS]
netbox-cli ip delete <address>
netbox-cli ip assign <address> --device DEVICE --interface IFACE
```

### Prefixe, Racks, VLANs
```bash
netbox-cli prefix list
netbox-cli rack list
netbox-cli rack info <name>     # Rack-Belegungsansicht (U-by-U)
netbox-cli vlan list
```

### Tenants & Kontakte
```bash
netbox-cli tenant list
netbox-cli contact list
```

---

## Netcup – Befehle

### Server-Übersicht
```bash
netbox-cli netcup list [-f table|json|csv]
netbox-cli netcup info <name|hostname|id>
netbox-cli netcup info <name> --raw       # Rohe API-JSON-Ausgabe
```

### Power-Management
```bash
netbox-cli netcup start <name> [--force]
netbox-cli netcup stop  <name> [--force]
netbox-cli netcup reset <name> [--force]  # Hard-Reset / Reboot
```

### Traffic-Statistik
```bash
netbox-cli netcup traffic             # Alle Server
netbox-cli netcup traffic <name>      # Einzelner Server
netbox-cli netcup traffic -f csv      # CSV-Export
```

### Snapshots
```bash
netbox-cli netcup snapshot list <name>
netbox-cli netcup snapshot create <name> [--snap-name NAME] [--description TEXT]
netbox-cli netcup snapshot delete <name> <snap_id> [--force]
netbox-cli netcup snapshot restore <name> <snap_id> [--force]
```

### NetBox-Integration
```bash
# Netcup VPS als VM in NetBox registrieren
netbox-cli netcup register <name>

# Live-Zustand (Status, IP, Interfaces) mit NetBox abgleichen
netbox-cli netcup sync
netbox-cli netcup sync --dry-run
netbox-cli netcup sync --sync-ip --sync-interfaces

# VM aus NetBox entfernen
netbox-cli netcup deregister <name>
```

`register` legt die VM in NetBox an, erstellt Interfaces mit MACs, setzt die primäre IP und schreibt die Tracking-Felder `vendor`, `janus_id`, `cpu_type` (werden automatisch als Custom Fields angelegt).  
`sync` gleicht nur VMs ab, die via `register` erfasst wurden (erkennbar an `vendor=netcup`).

---

## Shell-Completion

```bash
# Bash
eval "$(_NETBOX_CLI_COMPLETE=bash_source netbox-cli)"

# Zsh
eval "$(_NETBOX_CLI_COMPLETE=zsh_source netbox-cli)"

# Fish
eval (env _NETBOX_CLI_COMPLETE=fish_source netbox-cli)
```

Oder die Anleitung per CLI abrufen:
```bash
netbox-cli completion bash
netbox-cli completion zsh
netbox-cli completion fish
```

---

## Konfigurationsdateien

| Datei | Inhalt |
|-------|--------|
| `~/.config/netbox-cli/config.json` | NetBox URL + API-Token |
| `~/.config/netbox-cli/capabilities.json` | Gecachte Endpoint-Berechtigungen |
| `~/.config/netbox-cli/netcup.json` | Netcup Refresh-Token + Access-Token-Cache |

Alle Dateien werden mit Modus **0600** angelegt (nur für den eigenen User lesbar).
