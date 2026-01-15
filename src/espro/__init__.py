"""espro - Professional ESPHome infrastructure: manage devices without breaking entity IDs."""

from __future__ import annotations

from importlib.metadata import version

from .config import DatabaseConfig, ScanningConfig, Settings, get_settings
from .database import Database
from .models import DeviceRegistry, LogicalDevice, PhysicalDevice, ScanResult

__all__ = [
    "Database",
    "DatabaseConfig",
    "DeviceRegistry",
    "LogicalDevice",
    "PhysicalDevice",
    "ScanResult",
    "ScanningConfig",
    "Settings",
    "__version__",
    "get_settings",
]

__version__ = version("espro")
