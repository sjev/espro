"""Configuration loader following nora patterns."""

import os
from pathlib import Path

import platformdirs
import yaml
from pydantic import ValidationError

from espro.models.config import EsProConfig
from espro.models.device import DeviceRegistry


class ConfigLoader:
    """Load configuration and device registry.

    Directory resolution:
    1. ESPRO_DB environment variable (highest priority)
    2. platformdirs.user_data_dir("espro") - default
    """

    APP_NAME = "espro"
    CONFIG_FILE = "config.yaml"
    DEVICES_FILE = "devices.yaml"

    def __init__(self) -> None:
        """Initialize config loader."""
        self._db_dir = Path(
            os.environ.get("ESPRO_DB") or platformdirs.user_data_dir(self.APP_NAME)
        )
        self._physical_dir = self._db_dir / "physical"
        self._cache_dir = self._db_dir / "cache"

    @property
    def db_dir(self) -> Path:
        """Get database directory path."""
        return self._db_dir

    @property
    def config_path(self) -> Path:
        """Path to config.yaml."""
        return self._db_dir / self.CONFIG_FILE

    @property
    def devices_path(self) -> Path:
        """Path to devices.yaml."""
        return self._db_dir / self.DEVICES_FILE

    @property
    def current_scan_path(self) -> Path:
        """Path to current scan results."""
        return self._physical_dir / "current.json"

    def ensure_dirs(self) -> None:
        """Create directory structure if missing."""
        self._db_dir.mkdir(parents=True, exist_ok=True)
        self._physical_dir.mkdir(parents=True, exist_ok=True)
        self._cache_dir.mkdir(parents=True, exist_ok=True)

        # Create .gitignore for cache
        gitignore = self._cache_dir / ".gitignore"
        if not gitignore.exists():
            gitignore.write_text("*\n")

    def load_config(self) -> EsProConfig:
        """Load ESPro configuration from config.yaml."""
        if not self.config_path.exists():
            return EsProConfig()

        with open(self.config_path) as f:
            data = yaml.safe_load(f)

        try:
            return EsProConfig.model_validate(data or {})
        except ValidationError as e:
            raise ValueError(f"Invalid config file: {self.config_path}\n{e}") from e

    def save_config(self, config: EsProConfig) -> None:
        """Save ESPro configuration to config.yaml."""
        self.ensure_dirs()
        with open(self.config_path, "w") as f:
            yaml.dump(
                config.model_dump(exclude_none=True),
                f,
                default_flow_style=False,
                sort_keys=False,
            )

    def load_devices(self) -> DeviceRegistry:
        """Load device registry from devices.yaml."""
        if not self.devices_path.exists():
            return DeviceRegistry()

        with open(self.devices_path) as f:
            data = yaml.safe_load(f) or {}

        try:
            return DeviceRegistry.model_validate(data)
        except ValidationError as e:
            raise ValueError(f"Invalid devices file: {self.devices_path}\n{e}") from e

    def save_devices(self, registry: DeviceRegistry) -> None:
        """Save device registry to devices.yaml."""
        self.ensure_dirs()
        with open(self.devices_path, "w") as f:
            f.write("# ESPro Logical Device Registry\n")
            f.write("# Maps friendly logical names to physical ESPHome devices\n\n")
            yaml.dump(
                registry.model_dump(exclude_none=True),
                f,
                default_flow_style=False,
                sort_keys=False,
            )

    def create_default_config(self) -> None:
        """Initialize with default config and empty device registry."""
        self.ensure_dirs()

        if not self.config_path.exists():
            config = EsProConfig()
            self.save_config(config)

        if not self.devices_path.exists():
            registry = DeviceRegistry()
            self.save_devices(registry)
