from __future__ import annotations

import asyncio
import logging

import typer
from rich.console import Console
from rich.table import Table

from espro.commands import scan_network
from espro.utils.redaction import Redactor

from .common import build_database, load_settings_or_exit

logger = logging.getLogger(__name__)


def register(app: typer.Typer) -> None:
    @app.command()
    def scan(
        network: str | None = typer.Argument(
            None,
            help=(
                "Network to scan (e.g., 192.168.1.0/24). "
                "Uses config default if omitted."
            ),
        ),
        save: bool = typer.Option(True, help="Save scan results to data directory"),
        redact: bool = typer.Option(
            False,
            "--redact",
            help="Redact sensitive values in output",
        ),
    ) -> None:
        """Scan network for ESPHome devices."""
        console = Console()

        settings = load_settings_or_exit()
        db = build_database(settings)

        if network is None:
            network = settings.scanning.default_network
            console.print(f"Using network from config: {network}")

        console.print(f"Scanning {network} for ESPHome devices...")
        logger.info(
            "Scan settings: timeout=%.2fs, parallel_scans=%d",
            settings.scanning.timeout,
            settings.scanning.parallel_scans,
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
            logical_col = physical_to_logical.get(device.name, "")
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
