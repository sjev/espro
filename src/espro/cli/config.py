from __future__ import annotations

from typing import Annotated

import typer

from espro.config import Settings, render_settings_toml, write_settings

from .common import load_settings_or_exit, resolve_config_path_or_exit

app = typer.Typer(no_args_is_help=True)


@app.command("show")
def show_config() -> None:
    settings = load_settings_or_exit()
    path, exists = resolve_config_path_or_exit(allow_missing=True)

    source = str(path) if exists else "defaults"
    typer.echo(f"Config source: {source}")
    typer.echo(render_settings_toml(settings))


@app.command("init")
def init_config(
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help="Overwrite existing config"),
    ] = False,
) -> None:
    path, exists = resolve_config_path_or_exit(allow_missing=True)

    if exists and not force:
        typer.echo(f"Config already exists at {path}")
        return

    write_settings(Settings(), path)
    typer.echo(f"Wrote default config to {path}")
