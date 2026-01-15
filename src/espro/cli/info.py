from __future__ import annotations

import typer
from rich.console import Console

from .common import build_database, load_settings_or_exit, resolve_config_path_or_exit


def register(app: typer.Typer) -> None:
    @app.command()
    def info() -> None:
        """Show ESPro data directory info and stats."""
        settings = load_settings_or_exit()
        db = build_database(settings)
        registry = db.load_devices()
        current_scan = db.load_current_scan()

        config_path, config_exists = resolve_config_path_or_exit(allow_missing=True)

        console = Console()

        console.print("[bold]ESPro Info[/bold]\n")
        console.print(f"Data directory: {db.path}")
        console.print(f"Device registry: {db.devices_path}")
        console.print(f"Config file: {config_path if config_exists else 'defaults'}")

        console.print("\n[bold]Configuration[/bold]")
        console.print(f"Default network: {settings.scanning.default_network}")
        console.print(f"Port: {settings.scanning.port}")
        console.print(f"Timeout: {settings.scanning.timeout}s")

        console.print("\n[bold]Statistics[/bold]")
        console.print(f"Logical devices: {len(registry.logical_devices)}")

        if current_scan:
            console.print(f"Last scan: {current_scan.scan_timestamp}")
            console.print(f"Physical devices found: {len(current_scan.devices)}")
            console.print(f"Scan network: {current_scan.network}")
        else:
            console.print("No scans recorded yet")
