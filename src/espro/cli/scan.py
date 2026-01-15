from __future__ import annotations

import asyncio

import typer
from rich.console import Console
from rich.table import Table

from espro.commands import scan_network

from .common import build_database, load_settings_or_exit


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
    ) -> None:
        """Scan network for ESPHome devices."""
        console = Console()

        settings = load_settings_or_exit()
        db = build_database(settings)

        if network is None:
            network = settings.scanning.default_network
            console.print(f"Using network from config: {network}")

        console.print(f"Scanning {network} for ESPHome devices...")
        devices = asyncio.run(scan_network(network, settings.scanning))

        if not devices:
            console.print("No ESPHome devices found.")
            return

        table = Table()
        table.add_column("IP", style="cyan")
        table.add_column("Name", style="green")
        table.add_column("Friendly Name")
        table.add_column("MAC Address")
        table.add_column("Model")
        table.add_column("Version")

        for device in devices:
            table.add_row(
                device.ip,
                device.name,
                device.friendly_name,
                device.mac_address,
                device.model,
                device.esphome_version,
            )

        console.print(table)
        console.print(f"\n[green]Found {len(devices)} device(s)[/green]")

        if save:
            db.save_scan(devices, network)
            console.print(f"[green]✓[/green] Saved scan results to {db.path}")
