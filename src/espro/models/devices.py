from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class PhysicalDevice(BaseModel):
    model_config = {"extra": "forbid"}

    ip: str
    name: str
    friendly_name: str
    mac_address: str
    model: str
    esphome_version: str


class ScanResult(BaseModel):
    model_config = {"extra": "forbid"}

    scan_timestamp: datetime
    network: str
    devices: list[PhysicalDevice]


class LogicalDevice(BaseModel):
    model_config = {"extra": "forbid"}

    physical: str
    notes: str | None = None


class DeviceRegistry(BaseModel):
    model_config = {"extra": "forbid"}

    logical_devices: dict[str, LogicalDevice] = Field(default_factory=dict)
