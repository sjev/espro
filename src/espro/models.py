"""Data models for ESPro."""

from datetime import datetime

from pydantic import BaseModel, Field

# Configuration models


class ScanningConfig(BaseModel):
    """Scanning configuration."""

    default_network: str = "192.168.1.0/24"
    port: int = Field(default=6053, ge=1, le=65535)
    timeout: float = Field(default=5.0, gt=0)
    parallel_scans: int = Field(default=50, ge=1, le=255)


class EsProConfig(BaseModel):
    """Main ESPro configuration."""

    scanning: ScanningConfig = Field(default_factory=ScanningConfig)


# Device models


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
