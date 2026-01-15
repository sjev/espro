from __future__ import annotations

from pathlib import Path

import typer

from espro.config import (
    Settings,
    data_dir_from_settings,
    get_settings,
    resolve_config_path,
)
from espro.storage import Database


def load_settings_or_exit() -> Settings:
    try:
        return get_settings()
    except (FileNotFoundError, ValueError) as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc


def resolve_config_path_or_exit(allow_missing: bool = False) -> tuple[Path, bool]:
    try:
        return resolve_config_path(allow_missing=allow_missing)
    except FileNotFoundError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc


def build_database(settings: Settings, data_dir: Path | None = None) -> Database:
    path = data_dir or data_dir_from_settings(settings)
    return Database(path)
