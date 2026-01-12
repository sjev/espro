"""CLI for espro."""

import asyncio

import typer
from rich.console import Console
from rich.table import Table

from espro import __version__
from espro.scanner import detect_local_network, scan_network

app = typer.Typer(
    help="ESPro - Professional ESPHome infrastructure manager", no_args_is_help=True
)
devices_app = typer.Typer(help="Device management commands", no_args_is_help=True)
app.add_typer(devices_app, name="devices")


def version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        typer.echo(f"espro version {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False,
        "--version",
        "-v",
        help="Show version and exit",
        callback=version_callback,
        is_eager=True,
    ),
) -> None:
    """ESPro CLI."""
    pass


@devices_app.command("scan")
def devices_scan(
    network: str = typer.Argument(
        None,
        help="Network to scan (e.g., 192.168.1.0/24). Auto-detects if not provided.",
    ),
) -> None:
    """Scan network for ESPHome devices."""
    console = Console()

    if network is None:
        try:
            network = detect_local_network()
            console.print(f"Auto-detected network: {network}")
        except RuntimeError as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1) from None

    console.print(f"Scanning {network} for ESPHome devices...")
    devices = asyncio.run(scan_network(network))

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


if __name__ == "__main__":
    app()
