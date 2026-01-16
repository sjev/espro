from __future__ import annotations

import asyncio
import logging

import typer
from rich.console import Console
from rich.table import Table

from espro.cli.helpers import build_database, load_settings_or_exit
from espro.core import scan_network
from espro.utils.redaction import Redactor

logger = logging.getLogger(__name__)


def scan(
    network: str | None = typer.Argument(
        None,
        help=(
            "Optional scan label (ignored for mDNS discovery). Uses config default if "
            "omitted."
        ),
    ),
    save: bool = typer.Option(False, help="Save scan results to data directory"),
    redact: bool = typer.Option(
        False,
        "--redact",
        help="Redact sensitive values in output",
    ),
) -> None:
    """Discover ESPHome devices via mDNS."""
    console = Console()

    settings = load_settings_or_exit()
    db = build_database(settings)

    if network is None:
        network = settings.scanning.default_network
        console.print(
            f"Using scan label from config (ignored for discovery): {network}"
        )
    else:
        console.print(
            "Note: network argument is stored as a scan label; discovery uses mDNS."
        )

    console.print("Discovering ESPHome devices via mDNS...")
    logger.info(
        "mDNS discovery settings: timeout=%.2fs, label=%s",
        settings.scanning.timeout,
        network,
    )
    devices = asyncio.run(scan_network(network, settings.scanning))

    if not devices:
        console.print("No ESPHome devices found.")
        return

    # Build reverse lookup: physical name -> logical name
    registry = db.load_devices()
    physical_to_logical = {
        ld.physical: name for name, ld in registry.logical_devices.items()
    }

    redactor = Redactor(enabled=redact)
    table = Table()
    table.add_column("IP", style="cyan")
    table.add_column("Physical", style="green")
    table.add_column("Logical", style="yellow")
    table.add_column("MAC Address")
    table.add_column("Model")
    table.add_column("Version")

    for device in devices:
        # Format: "name (Friendly Name)" or just "name"
        if device.friendly_name:
            physical_col = f"{device.name} ({device.friendly_name})"
        else:
            physical_col = device.name
        logical_col = (
            physical_to_logical.get(device.ip)
            or physical_to_logical.get(device.name)
            or physical_to_logical.get(f"{device.name}.local")
            or ""
        )
        table.add_row(
            redactor.redact_ip(device.ip),
            physical_col,
            logical_col,
            redactor.redact_mac(device.mac_address),
            device.model,
            redactor.redact_version(device.esphome_version),
        )

    console.print(table)
    console.print(f"\n[green]Found {len(devices)} device(s)[/green]")

    if save:
        db.save_scan(devices, network)
        console.print(f"[green]✓[/green] Saved scan results to {db.path}")


def register(app: typer.Typer) -> None:
    app.command()(scan)
