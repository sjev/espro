from __future__ import annotations

import asyncio

import typer
from rich.console import Console

from espro.commands import run_mock_device


def register(app: typer.Typer) -> None:
    @app.command()
    def mock(
        name: str = typer.Option("mock-switch-1", "--name", "-n", help="Device name"),
        port: int = typer.Option(6053, "--port", "-p", help="Port to listen on"),
        mac: str = typer.Option(
            "AA:BB:CC:DD:EE:FF", "--mac", help="MAC address to report"
        ),
    ) -> None:
        """Run a mock ESPHome device for development."""
        console = Console()
        console.print(f"Starting mock device '{name}' on port {port}...")
        console.print("Press Ctrl+C to stop.\n")

        try:
            asyncio.run(run_mock_device(name=name, port=port, mac_address=mac))
        except KeyboardInterrupt:
            console.print("\n[green]Mock device stopped.[/green]")
