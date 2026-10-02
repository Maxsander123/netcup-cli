from __future__ import annotations

import json

from rich import box
from rich.console import Console
from rich.table import Table

console = Console()


def _is_task(value: object) -> bool:
    return isinstance(value, dict) and "uuid" in value and "taskProgress" in value and "state" in value


def _wait_task(task: dict) -> dict:
    import time

    import click

    from netcup_cli.client import build_client
    from netcup_cli.errors import CLIError

    uuid = task["uuid"]
    client = build_client()
    from contextlib import nullcontext

    try:
        spinner = console.status(f"{task.get('name', 'Task')} …") if console.is_terminal else nullcontext()
        with spinner as status:
            while task.get("state") in ("PENDING", "RUNNING", "WAITING_FOR_CANCEL"):
                if status is not None:
                    pct = (task.get("taskProgress") or {}).get("progressInPercent") or 0
                    status.update(f"{task.get('message') or task.get('name')} [dim]({pct:.0f}%)[/dim]")
                time.sleep(2)
                task = client.request("GET", f"/tasks/{uuid}")  # type: ignore[assignment]
    except KeyboardInterrupt:
        console.print(f"\n[yellow]Still running in background.[/yellow] Check: netcup-cli tasks get {uuid}")
        raise click.exceptions.Exit(130)
    if task.get("state") != "FINISHED":
        err = task.get("responseError") or {}
        detail = err.get("message") if isinstance(err, dict) else err
        raise CLIError(f"Task {task.get('name')} {task.get('state')}: {detail or task.get('message') or ''}".strip())
    return task


def _print_task(value: dict) -> None:
    import click

    ctx = click.get_current_context(silent=True)
    wait = not (ctx and ctx.find_root().obj and ctx.find_root().obj.get("no_wait"))
    if wait:
        value = _wait_task(value)
        console.print(f"[green]✓[/green] {value.get('message') or value.get('name')}")
    else:
        console.print(f"Task [cyan]{value['uuid']}[/cyan] {value.get('state')} — netcup-cli tasks get {value['uuid']}")


def print_result(value: object, *, as_json: bool = False) -> None:
    if _is_task(value):
        if as_json:
            import click

            ctx = click.get_current_context(silent=True)
            if not (ctx and ctx.find_root().obj and ctx.find_root().obj.get("no_wait")):
                value = _wait_task(value)  # type: ignore[arg-type]
        else:
            _print_task(value)  # type: ignore[arg-type]
            return
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

    # ── General info ──────────────────────────────────────────────────────────
    t = Table(box=box.SIMPLE, show_header=False, padding=(0, 1))
    t.add_column("Key", style="bold", no_wrap=True)
    t.add_column("Value")

    def _row(key: str, val: object) -> None:
        if val is None or val == "" or val == {} or val == []:
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
    _row("Site", (data.get("site") or {}).get("city"))

    live = data.get("serverLiveInfo") or {}
    _row("State", live.get("state"))
    _row("vCPUs", live.get("cpuCount"))
    mem = live.get("currentServerMemoryInMiB")
    _row("Memory", f"{mem} MiB ({mem // 1024} GiB)" if mem else None)

    up = live.get("uptimeInSeconds")
    if up:
        _row("Uptime", f"{up // 86400}d {up % 86400 // 3600}h {up % 3600 // 60}m")

    for disk in live.get("disks") or []:
        cap = disk.get("capacityInMiB") or 0
        used = disk.get("allocationInMiB")
        used_s = f", {used // 1024} GiB used" if used is not None else ""
        _row(f"Disk {disk.get('dev', '?')}", f"{cap // 1024} GiB ({disk.get('driver', '')}{used_s})")

    v4 = [a.get("ip") for a in data.get("ipv4Addresses") or [] if a.get("ip")]
    _row("IPv4", ", ".join(v4))
    v6 = [f"{a.get('networkPrefix')}/{a.get('networkPrefixLength')}" for a in data.get("ipv6Addresses") or []]
    _row("IPv6", ", ".join(v6))

    shown = {"id", "nickname", "hostname", "template", "disabled", "serverLiveInfo", "site",
             "ipv4Addresses", "ipv6Addresses"}
    for k, v in data.items():
        if k not in shown:
            _row(k, v)

    console.print(t)

    # ── Interfaces ────────────────────────────────────────────────────────────
    ifaces = live.get("interfaces") or []
    if ifaces:
        console.print()
        iface_t = Table(box=box.ROUNDED, title="Interfaces")
        iface_t.add_column("#", style="dim", no_wrap=True)
        iface_t.add_column("MAC", style="cyan", no_wrap=True)
        iface_t.add_column("IPv4", overflow="fold")
        iface_t.add_column("IPv6 Prefix", overflow="fold")
        iface_t.add_column("VLAN")
        iface_t.add_column("RX / TX (month)")

        for idx, iface in enumerate(ifaces):
            mac = iface.get("mac") or "—"
            ips = iface.get("ipv4Addresses") or []
            ipv4 = "\n".join(ips) if ips else "—"
            ipv6_prefixes = iface.get("ipv6NetworkPrefixes") or []
            ipv6 = "\n".join(ipv6_prefixes) if ipv6_prefixes else "—"
            vlan_id = iface.get("vlanId")
            vlan = str(vlan_id) if vlan_id else ("VLAN" if iface.get("vlanInterface") else "—")
            rx = iface.get("rxMonthlyInMiB", 0) or 0
            tx = iface.get("txMonthlyInMiB", 0) or 0
            traffic = f"{rx / 1024:.1f} GiB / {tx / 1024:.1f} GiB"
            iface_t.add_row(str(idx), mac, ipv4, ipv6, vlan, traffic)

        console.print(iface_t)


_SUMMARY_KEYS = ("name", "username", "city", "ip", "cidr", "progressInPercent", "key", "id")


def _cell(v: object) -> str:
    if v is None or v == "":
        return "—"
    if isinstance(v, dict):
        for k in _SUMMARY_KEYS:
            if v.get(k) not in (None, ""):
                return f"{v[k]}%" if k == "progressInPercent" else str(v[k])
        return json.dumps(v, ensure_ascii=False)
    if isinstance(v, list):
        return ", ".join(_cell(i) for i in v) or "—"
    return str(v)


def _print_table(rows: list[dict]) -> None:
    keys = list(rows[0].keys())
    t = Table(box=box.ROUNDED)
    for k in keys:
        t.add_column(str(k), overflow="fold")
    for row in rows:
        t.add_row(*(_cell(row.get(k)) for k in keys))
    console.print(t)


def _print_dict(d: dict) -> None:
    t = Table(box=box.SIMPLE, show_header=False)
    t.add_column("Key", style="bold")
    t.add_column("Value", overflow="fold")
    for k, v in d.items():
        t.add_row(str(k), json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else _cell(v))
    console.print(t)
