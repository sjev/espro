from __future__ import annotations

import json
import os
import tomllib
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field, ValidationError

from .paths import default_config_path, default_data_dir, expand_path

CONFIG_ENV_VAR = "ESPRO_CONFIG"


class DatabaseConfig(BaseModel):
    model_config = {"frozen": True, "extra": "forbid"}

    path: str = Field(default_factory=lambda: str(default_data_dir()))


class ScanningConfig(BaseModel):
    model_config = {"frozen": True, "extra": "forbid"}

    default_network: str = "192.168.1.0/24"
    port: int = Field(default=6053, ge=1, le=65535)
    timeout: float = Field(default=5.0, gt=0)
    parallel_scans: int = Field(default=50, ge=1, le=255)


class Settings(BaseModel):
    model_config = {"frozen": True, "extra": "forbid"}

    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    scanning: ScanningConfig = Field(default_factory=ScanningConfig)


def resolve_config_path(allow_missing: bool = False) -> tuple[Path, bool]:
    env_path = os.environ.get(CONFIG_ENV_VAR)
    if env_path:
        path = expand_path(env_path)
        if not allow_missing and not path.exists():
            raise FileNotFoundError(f"{CONFIG_ENV_VAR} points to missing file: {path}")
        return path, path.exists()

    path = default_config_path()
    return path, path.exists()


def load_settings(path: Path) -> Settings:
    try:
        with path.open("rb") as handle:
            data = tomllib.load(handle)
    except tomllib.TOMLDecodeError as exc:
        raise ValueError(f"Invalid TOML in config file: {path}\\n{exc}") from exc

    try:
        return Settings.model_validate(data or {})
    except ValidationError as exc:
        raise ValueError(f"Invalid config file: {path}\n{exc}") from exc


@lru_cache
def get_settings() -> Settings:
    path, exists = resolve_config_path(allow_missing=False)
    if exists:
        return load_settings(path)
    return Settings()


def data_dir_from_settings(settings: Settings) -> Path:
    return expand_path(settings.database.path)


def _toml_string(value: str) -> str:
    return json.dumps(value)


def render_settings_toml(settings: Settings) -> str:
    lines = [
        "# ESPro configuration",
        "",
        "[database]",
        f"path = {_toml_string(settings.database.path)}",
        "",
        "[scanning]",
        f"default_network = {_toml_string(settings.scanning.default_network)}",
        f"port = {settings.scanning.port}",
        f"timeout = {settings.scanning.timeout}",
        f"parallel_scans = {settings.scanning.parallel_scans}",
        "",
    ]
    return "\n".join(lines)


def write_settings(settings: Settings, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_settings_toml(settings))
