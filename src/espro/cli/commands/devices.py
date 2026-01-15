from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table

from espro.cli.helpers import build_database, load_settings_or_exit


def list_devices() -> None:
    """List logical device mappings."""
    settings = load_settings_or_exit()
    db = build_database(settings)
    registry = db.load_devices()

    console = Console()

    if not registry.logical_devices:
        console.print("No logical devices defined.")
        console.print(f"Use 'espro add' to create mappings or edit {db.devices_path}")
        return

    table = Table()
    table.add_column("Logical Name", style="cyan")
    table.add_column("Physical Device", style="green")
    table.add_column("Notes")

    for name, device in sorted(registry.logical_devices.items()):
        table.add_row(name, device.physical, device.notes or "")

    console.print(table)


def add_device(
    name: str = typer.Argument(..., help="Logical device name"),
    physical: str = typer.Argument(..., help="Physical device (hostname or IP)"),
    notes: str | None = typer.Option(None, "--notes", help="Optional notes"),
) -> None:
    """Add or update a logical device mapping."""
    settings = load_settings_or_exit()
    db = build_database(settings)
    db.add_logical_device(name, physical, notes)

    console = Console()
    console.print(f"[green]✓[/green] Mapped '{name}' → '{physical}'")


def remove_device(name: str = typer.Argument(..., help="Logical device name")) -> None:
    """Remove a logical device mapping."""
    settings = load_settings_or_exit()
    db = build_database(settings)

    console = Console()
    if db.remove_logical_device(name):
        console.print(f"[green]✓[/green] Removed device '{name}'")
    else:
        console.print(f"[yellow]![/yellow] Device '{name}' not found")
        raise typer.Exit(1)


def register(app: typer.Typer) -> None:
    app.command("list")(list_devices)
    app.command("add")(add_device)
    app.command("remove")(remove_device)
