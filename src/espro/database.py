"""Main database interface."""

import os
from pathlib import Path

from espro.config.loader import ConfigLoader
from espro.models.config import EsProConfig
from espro.models.device import (
    DeviceRegistry,
    LogicalDevice,
    PhysicalDevice,
    ScanResult,
)
from espro.storage.physical import PhysicalDeviceStorage


class Database:
    """Main database interface for ESPro.

    Usage:
        db = Database()  # Uses ESPRO_DB or default

        # Save scan results
        devices = [PhysicalDevice(...), ...]
        db.save_scan(devices, network="192.168.1.0/24")

        # Manage logical devices
        db.add_logical_device("outdoor_light", "esp-sonoff-1.local")
    """

    def __init__(self, path: Path | None = None) -> None:
        """Initialize database."""
        if path:
            os.environ["ESPRO_DB"] = str(path)

        self._loader = ConfigLoader()
        self._loader.ensure_dirs()

        self._physical_storage = PhysicalDeviceStorage(self._loader._physical_dir)

    @property
    def path(self) -> Path:
        """Get database directory path."""
        return self._loader.db_dir

    # Configuration
    def get_config(self) -> EsProConfig:
        """Load ESPro configuration."""
        return self._loader.load_config()

    def save_config(self, config: EsProConfig) -> None:
        """Save ESPro configuration."""
        self._loader.save_config(config)

    # Device Registry (Logical)
    def get_devices(self) -> DeviceRegistry:
        """Load logical device registry."""
        return self._loader.load_devices()

    def save_devices(self, registry: DeviceRegistry) -> None:
        """Save logical device registry."""
        self._loader.save_devices(registry)

    def add_logical_device(
        self, name: str, physical: str, notes: str | None = None
    ) -> None:
        """Add or update a logical device mapping."""
        registry = self.get_devices()
        registry.logical_devices[name] = LogicalDevice(physical=physical, notes=notes)
        self.save_devices(registry)

    def remove_logical_device(self, name: str) -> bool:
        """Remove a logical device. Returns True if existed."""
        registry = self.get_devices()
        if name in registry.logical_devices:
            del registry.logical_devices[name]
            self.save_devices(registry)
            return True
        return False

    # Physical Device Scans
    def save_scan(self, devices: list[PhysicalDevice], network: str) -> None:
        """Save scan results."""
        self._physical_storage.save_scan(devices, network)

    def get_current_scan(self) -> ScanResult | None:
        """Get most recent scan results."""
        return self._physical_storage.load_current()

    # Initialization
    def init(self) -> None:
        """Initialize database with default config and empty registry."""
        self._loader.create_default_config()
