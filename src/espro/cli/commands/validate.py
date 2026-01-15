from __future__ import annotations

import typer
from rich.console import Console

from espro.cli.helpers import build_database, load_settings_or_exit
from espro.core import validate_mappings


def register(app: typer.Typer) -> None:
    @app.command()
    def validate() -> None:
        """Validate logical device mappings against scan results."""
        settings = load_settings_or_exit()
        db = build_database(settings)
        registry = db.load_devices()
        current_scan = db.load_current_scan()

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

        if result.errors:
            console.print("[red]✗[/red] Validation errors:\n")
            for error in result.errors:
                console.print(f"  [red]•[/red] {error}")
            console.print()

        if result.warnings:
            console.print("[yellow]⚠[/yellow] Warnings:\n")
            for warning in result.warnings:
                console.print(f"  [yellow]•[/yellow] {warning}")
            console.print()

        if result.valid_count > 0:
            console.print(
                f"[green]✓[/green] {result.valid_count} device(s) validated successfully"
            )

        if result.unmapped_devices:
            console.print(
                f"\n[blue]i[/blue] {len(result.unmapped_devices)} unmapped physical device(s):"
            )
            for name, ip in result.unmapped_devices:
                console.print(f"  • {name} ({ip})")

        if result.errors:
            raise typer.Exit(1)
