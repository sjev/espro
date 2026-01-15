from __future__ import annotations

import os
from pathlib import Path

APP_NAME = "espro"
CONFIG_FILENAME = "config.toml"


def xdg_config_home() -> Path:
    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))


def xdg_data_home() -> Path:
    return Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))


def default_config_path() -> Path:
    return xdg_config_home() / APP_NAME / CONFIG_FILENAME


def default_data_dir() -> Path:
    return xdg_data_home() / APP_NAME


def expand_path(value: str) -> Path:
    return Path(os.path.expandvars(os.path.expanduser(value)))
