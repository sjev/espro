from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from espro.cli.helpers import build_database
from espro.config import Settings, resolve_config_path, write_settings


def register(app: typer.Typer) -> None:
    @app.command()
    def init(
        data_dir: Annotated[
            Path | None,
            typer.Option("--data-dir", "--path", help="Custom data directory"),
        ] = None,
        force: Annotated[
            bool,
            typer.Option("--force", "-f", help="Overwrite existing config and data"),
        ] = False,
    ) -> None:
        """Initialize ESPro configuration and data directory."""
        console = Console()

        # Initialize config
        config_path, config_exists = resolve_config_path(allow_missing=True)
        if config_exists and not force:
            console.print(f"[dim]Config exists:[/dim] {config_path}")
        else:
            write_settings(Settings(), config_path)
            action = "Overwrote" if config_exists else "Created"
            console.print(f"[green]✓[/green] {action} config: {config_path}")

        # Initialize data directory
        settings = Settings()
        db = build_database(settings, data_dir=data_dir)
        created = db.init(force=force)

        if created:
            console.print(f"[green]✓[/green] Initialized data dir: {db.path}")
        else:
            console.print(f"[dim]Data dir exists:[/dim] {db.path}")
