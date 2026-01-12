"""Configuration and storage management."""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import platformdirs
import yaml
from pydantic import ValidationError

from espro.models import DeviceRegistry, EsProConfig, PhysicalDevice, ScanResult

APP_NAME = "espro"
CONFIG_FILE = "config.yaml"
DEVICES_FILE = "devices.yaml"


class ConfigLoader:
    """Load configuration and device registry.

    Directory resolution:
    1. ESPRO_DB environment variable (highest priority)
    2. platformdirs.user_data_dir("espro") - default
    """

    def __init__(self) -> None:
        """Initialize config loader."""
        self._db_dir = Path(
            os.environ.get("ESPRO_DB") or platformdirs.user_data_dir(APP_NAME)
        )
        self._physical_dir = self._db_dir / "physical"
        self._cache_dir = self._db_dir / "cache"

    @property
    def db_dir(self) -> Path:
        """Get database directory path."""
        return self._db_dir

    @property
    def physical_dir(self) -> Path:
        """Get physical devices directory path."""
        return self._physical_dir

    @property
    def config_path(self) -> Path:
        """Path to config.yaml."""
        return self._db_dir / CONFIG_FILE

    @property
    def devices_path(self) -> Path:
        """Path to devices.yaml."""
        return self._db_dir / DEVICES_FILE

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


class PhysicalDeviceStorage:
    """Storage for physical device scan results."""

    def __init__(self, physical_dir: Path) -> None:
        self.physical_dir = physical_dir
        self.current_path = physical_dir / "current.json"

    def save_scan(self, devices: list[PhysicalDevice], network: str) -> None:
        """Save scan results to current.json."""
        scan = ScanResult(
            scan_timestamp=datetime.now(timezone.utc),
            network=network,
            devices=devices,
        )

        self.physical_dir.mkdir(parents=True, exist_ok=True)
        with open(self.current_path, "w") as f:
            json.dump(scan.model_dump(mode="json"), f, indent=2)

    def load_current(self) -> ScanResult | None:
        """Load current scan results."""
        if not self.current_path.exists():
            return None

        with open(self.current_path) as f:
            data = json.load(f)

        return ScanResult.model_validate(data)
