from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from .common import build_database, load_settings_or_exit, resolve_config_path_or_exit


def register(app: typer.Typer) -> None:
    @app.command()
    def init(
        data_dir: Annotated[
            Path | None,
            typer.Option("--data-dir", "--path", help="Custom data directory"),
        ] = None,
    ) -> None:
        """Initialize ESPro data directory."""
        console = Console()

        settings = load_settings_or_exit()
        db = build_database(settings, data_dir=data_dir)
        db.init()

        console.print(f"[green]✓[/green] Initialized ESPro data dir at: {db.path}")
        console.print(f"  • {db.devices_path} - Device registry")

        config_path, config_exists = resolve_config_path_or_exit(allow_missing=True)
        if not config_exists:
            console.print("\nConfig not found. Run 'espro config init' to create one.")
        else:
            console.print(f"  • {config_path} - Configuration")
