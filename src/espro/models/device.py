"""Device models."""

from datetime import datetime

from pydantic import BaseModel


class PhysicalDevice(BaseModel):
    """Physical ESPHome device (from scan)."""

    ip: str
    name: str
    friendly_name: str
    mac_address: str
    model: str
    esphome_version: str


class ScanResult(BaseModel):
    """Complete scan result."""

    scan_timestamp: datetime
    network: str
    devices: list[PhysicalDevice]


class LogicalDevice(BaseModel):
    """Logical device mapping."""

    physical: str  # hostname or IP
    notes: str | None = None


class DeviceRegistry(BaseModel):
    """Complete logical device registry."""

    logical_devices: dict[str, LogicalDevice] = {}
