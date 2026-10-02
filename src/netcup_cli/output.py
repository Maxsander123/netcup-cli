from __future__ import annotations

import json

from rich import box
from rich.console import Console
from rich.table import Table

console = Console()


def print_result(value: object, *, as_json: bool = False) -> None:
    if as_json:
        print(json.dumps(value, indent=2, default=str))
        return
    if value is None:
        console.print("[dim]Done.[/dim]")
        return
    if isinstance(value, list):
        if not value:
            console.print("[dim]No results.[/dim]")
            return
        if isinstance(value[0], dict):
            _print_table(value)
        else:
            for item in value:
                console.print(str(item))
    elif isinstance(value, dict):
        _print_dict(value)
    else:
        console.print(str(value))


def print_servers(servers: list[dict], *, as_json: bool = False) -> None:
    if as_json:
        print(json.dumps(servers, indent=2, default=str))
        return
    if not servers:
        console.print("[dim]No servers.[/dim]")
        return
    t = Table(box=box.ROUNDED)
    t.add_column("ID", style="cyan", no_wrap=True)
    t.add_column("Nickname", style="bold")
    t.add_column("Hostname")
    t.add_column("Template")
    t.add_column("Disabled")
    for s in servers:
        tmpl = s.get("template") or {}
        tmpl_name = tmpl.get("name", "") if isinstance(tmpl, dict) else str(tmpl)
        t.add_row(
            str(s.get("id", "")),
            str(s.get("nickname") or "—"),
            str(s.get("hostname") or "—"),
            tmpl_name,
            "yes" if s.get("disabled") else "no",
        )
    console.print(t)
    console.print(f"[dim]{len(servers)} server(s)[/dim]")


def print_server(data: dict, *, as_json: bool = False) -> None:
    if as_json:
        print(json.dumps(data, indent=2, default=str))
        return
    t = Table(box=box.SIMPLE, show_header=False)
    t.add_column("Key", style="bold", no_wrap=True)
    t.add_column("Value")

    def _row(key: str, val: object) -> None:
        if val is None or val == "" or val == {}:
            return
        if isinstance(val, (dict, list)):
            t.add_row(key, json.dumps(val, ensure_ascii=False))
        else:
            t.add_row(key, str(val))

    _row("ID", data.get("id"))
    _row("Nickname", data.get("nickname"))
    _row("Hostname", data.get("hostname"))
    tmpl = data.get("template")
    if isinstance(tmpl, dict):
        _row("Template", tmpl.get("name", json.dumps(tmpl)))
    elif tmpl:
        _row("Template", tmpl)
    _row("Disabled", data.get("disabled"))

    live = data.get("serverLiveInfo") or {}
    _row("State", live.get("state"))
    _row("vCPUs", live.get("cpuCount"))
    mem = live.get("currentServerMemoryInMiB")
    _row("Memory", f"{mem} MiB" if mem else None)

    ifaces = live.get("interfaces") or []
    for i, iface in enumerate(ifaces):
        prefix = f"Interface {i}"
        _row(f"{prefix} MAC", iface.get("mac"))
        for addr in iface.get("ipAddresses") or []:
            _row(f"{prefix} IP", addr.get("ip"))
        for pfx in iface.get("ipv6NetworkPrefixes") or []:
            _row(f"{prefix} IPv6", pfx)

    disks = live.get("disks") or []
    for i, disk in enumerate(disks):
        _row(f"Disk {i} ID", disk.get("id"))
        cap = disk.get("capacityInMiB")
        _row(f"Disk {i} Size", f"{cap} MiB ({cap // 1024} GiB)" if cap else None)

    _row("Site", (data.get("site") or {}).get("city"))

    # Remaining top-level fields not already shown
    shown = {"id", "nickname", "hostname", "template", "disabled", "serverLiveInfo", "site"}
    for k, v in data.items():
        if k not in shown:
            _row(k, v)

    console.print(t)


def _print_table(rows: list[dict]) -> None:
    keys = list(rows[0].keys())
    t = Table(box=box.ROUNDED)
    for k in keys:
        t.add_column(str(k))
    for row in rows:
        val_strs = []
        for k in keys:
            v = row.get(k, "")
            val_strs.append(json.dumps(v) if isinstance(v, (dict, list)) else str(v))
        t.add_row(*val_strs)
    console.print(t)


def _print_dict(d: dict) -> None:
    t = Table(box=box.SIMPLE, show_header=False)
    t.add_column("Key", style="bold")
    t.add_column("Value")
    for k, v in d.items():
        t.add_row(str(k), json.dumps(v) if isinstance(v, (dict, list)) else str(v))
    console.print(t)
