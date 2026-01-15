from __future__ import annotations

import typer

from espro.cli.helpers import load_settings_or_exit, resolve_config_path_or_exit
from espro.config import render_settings_toml

app = typer.Typer(no_args_is_help=True)


@app.command("show")
def show_config() -> None:
    """Show current configuration."""
    settings = load_settings_or_exit()
    path, exists = resolve_config_path_or_exit(allow_missing=True)

    source = str(path) if exists else "defaults"
    typer.echo(f"Config source: {source}")
    typer.echo(render_settings_toml(settings))
