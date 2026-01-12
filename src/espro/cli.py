"""CLI for espro."""

import asyncio
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from espro import __version__
from espro.database import Database
from espro.logging import setup_logging
from espro.scanner import scan_network
from espro.services import validate_mappings

setup_logging()

app = typer.Typer(
    help="ESPro - Professional ESPHome infrastructure manager", no_args_is_help=True
)


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


@app.command()
def init(
    path: str | None = typer.Option(
        None,
        "--path",
        help="Custom database directory (overrides ESPRO_DB)",
    ),
) -> None:
    """Initialize ESPro database with default configuration."""
    console = Console()

    db = Database(Path(path) if path else None)
    db.init()

    console.print(f"[green]✓[/green] Initialized ESPro database at: {db.path}")
    console.print("\nCreated:")
    console.print(f"  • {db.path / 'config.yaml'} - Configuration")
    console.print(f"  • {db.path / 'devices.yaml'} - Device registry")


@app.command()
def scan(
    network: str | None = typer.Argument(
        None,
        help="Network to scan (e.g., 192.168.1.0/24). Uses config.yaml default if omitted.",
    ),
    save: bool = typer.Option(True, help="Save scan results to database"),
) -> None:
    """Scan network for ESPHome devices."""
    console = Console()

    db = Database()

    # Get network from argument or config
    if network is None:
        config = db.get_config()
        network = config.scanning.default_network
        console.print(f"Using network from config: {network}")

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
    console.print(f"\n[green]Found {len(devices)} device(s)[/green]")

    if save:
        db.save_scan(devices, network)
        console.print(f"[green]✓[/green] Saved scan results to {db.path}")


@app.command("list")
def list_devices() -> None:
    """List logical device mappings."""
    db = Database()
    registry = db.get_devices()

    console = Console()

    if not registry.logical_devices:
        console.print("No logical devices defined.")
        console.print(
            f"Use 'espro add' to create mappings or edit {db.path / 'devices.yaml'}"
        )
        return

    table = Table()
    table.add_column("Logical Name", style="cyan")
    table.add_column("Physical Device", style="green")
    table.add_column("Notes")

    for name, device in sorted(registry.logical_devices.items()):
        table.add_row(name, device.physical, device.notes or "")

    console.print(table)


@app.command()
def add(
    name: str = typer.Argument(..., help="Logical device name"),
    physical: str = typer.Argument(..., help="Physical device (hostname or IP)"),
    notes: str | None = typer.Option(None, "--notes", help="Optional notes"),
) -> None:
    """Add or update a logical device mapping."""
    db = Database()
    db.add_logical_device(name, physical, notes)

    console = Console()
    console.print(f"[green]✓[/green] Mapped '{name}' → '{physical}'")


@app.command()
def remove(
    name: str = typer.Argument(..., help="Logical device name"),
) -> None:
    """Remove a logical device mapping."""
    db = Database()

    console = Console()
    if db.remove_logical_device(name):
        console.print(f"[green]✓[/green] Removed device '{name}'")
    else:
        console.print(f"[yellow]![/yellow] Device '{name}' not found")
        raise typer.Exit(1)


@app.command()
def info() -> None:
    """Show ESPro database info and statistics."""
    db = Database()
    config = db.get_config()
    registry = db.get_devices()
    current_scan = db.get_current_scan()

    console = Console()

    console.print("[bold]ESPro Database Info[/bold]\n")
    console.print(f"Database path: {db.path}")
    console.print(f"Config file: {db.path / 'config.yaml'}")
    console.print(f"Devices file: {db.path / 'devices.yaml'}")

    console.print("\n[bold]Configuration[/bold]")
    console.print(f"Default network: {config.scanning.default_network}")
    console.print(f"Port: {config.scanning.port}")
    console.print(f"Timeout: {config.scanning.timeout}s")

    console.print("\n[bold]Statistics[/bold]")
    console.print(f"Logical devices: {len(registry.logical_devices)}")

    if current_scan:
        console.print(f"Last scan: {current_scan.scan_timestamp}")
        console.print(f"Physical devices found: {len(current_scan.devices)}")
        console.print(f"Scan network: {current_scan.network}")
    else:
        console.print("No scans recorded yet")


@app.command()
def validate() -> None:
    """Validate logical device mappings against scan results."""
    db = Database()
    registry = db.get_devices()
    current_scan = db.get_current_scan()

    console = Console()

    if not current_scan:
        console.print(
            "[yellow]⚠[/yellow] No scan results available. Run 'espro scan' first."
        )
        raise typer.Exit(1)

    if not registry.logical_devices:
        console.print("[yellow]⚠[/yellow] No logical devices defined.")
        return

    result = validate_mappings(registry, current_scan)

    # Report errors
    if result.errors:
        console.print("[red]✗[/red] Validation errors:\n")
        for error in result.errors:
            console.print(f"  [red]•[/red] {error}")
        console.print()

    # Report warnings
    if result.warnings:
        console.print("[yellow]⚠[/yellow] Warnings:\n")
        for warning in result.warnings:
            console.print(f"  [yellow]•[/yellow] {warning}")
        console.print()

    # Report successes
    if result.valid_count > 0:
        console.print(
            f"[green]✓[/green] {result.valid_count} device(s) validated successfully"
        )

    # Show unmapped physical devices
    if result.unmapped_devices:
        console.print(
            f"\n[blue]i[/blue] {len(result.unmapped_devices)} unmapped physical device(s):"
        )
        for name, ip in result.unmapped_devices:
            console.print(f"  • {name} ({ip})")

    if result.errors:
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
