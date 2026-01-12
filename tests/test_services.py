"""Tests for services."""

from datetime import datetime, timezone

from espro.models import (
    DeviceRegistry,
    LogicalDevice,
    PhysicalDevice,
    ScanResult,
)
from espro.services import validate_mappings


def test_validate_mappings_all_valid():
    """Test validation with all mappings valid."""
    registry = DeviceRegistry(
        logical_devices={
            "kitchen_light": LogicalDevice(physical="esp-kitchen"),
            "garage_sensor": LogicalDevice(physical="192.168.1.20"),
        }
    )
    scan = ScanResult(
        scan_timestamp=datetime.now(timezone.utc),
        network="192.168.1.0/24",
        devices=[
            PhysicalDevice(
                ip="192.168.1.10",
                name="esp-kitchen",
                friendly_name="Kitchen",
                mac_address="AA:BB:CC:DD:EE:01",
                model="ESP32",
                esphome_version="2024.1.0",
            ),
            PhysicalDevice(
                ip="192.168.1.20",
                name="esp-garage",
                friendly_name="Garage",
                mac_address="AA:BB:CC:DD:EE:02",
                model="ESP32",
                esphome_version="2024.1.0",
            ),
        ],
    )

    result = validate_mappings(registry, scan)

    assert result.valid_count == 2
    assert result.errors == []
    assert result.unmapped_devices == []


def test_validate_mappings_missing_device():
    """Test validation with missing physical device."""
    registry = DeviceRegistry(
        logical_devices={
            "kitchen_light": LogicalDevice(physical="esp-missing"),
        }
    )
    scan = ScanResult(
        scan_timestamp=datetime.now(timezone.utc),
        network="192.168.1.0/24",
        devices=[
            PhysicalDevice(
                ip="192.168.1.10",
                name="esp-kitchen",
                friendly_name="Kitchen",
                mac_address="AA:BB:CC:DD:EE:01",
                model="ESP32",
                esphome_version="2024.1.0",
            ),
        ],
    )

    result = validate_mappings(registry, scan)

    assert result.valid_count == 0
    assert len(result.errors) == 1
    assert "esp-missing" in result.errors[0]
    assert len(result.unmapped_devices) == 1


def test_validate_mappings_with_local_suffix():
    """Test validation handles .local suffix."""
    registry = DeviceRegistry(
        logical_devices={
            "kitchen_light": LogicalDevice(physical="esp-kitchen.local"),
        }
    )
    scan = ScanResult(
        scan_timestamp=datetime.now(timezone.utc),
        network="192.168.1.0/24",
        devices=[
            PhysicalDevice(
                ip="192.168.1.10",
                name="esp-kitchen",
                friendly_name="Kitchen",
                mac_address="AA:BB:CC:DD:EE:01",
                model="ESP32",
                esphome_version="2024.1.0",
            ),
        ],
    )

    result = validate_mappings(registry, scan)

    assert result.valid_count == 1
    assert result.errors == []


def test_validate_mappings_unmapped_devices():
    """Test detection of unmapped physical devices."""
    registry = DeviceRegistry(logical_devices={})
    scan = ScanResult(
        scan_timestamp=datetime.now(timezone.utc),
        network="192.168.1.0/24",
        devices=[
            PhysicalDevice(
                ip="192.168.1.10",
                name="esp-orphan",
                friendly_name="Orphan",
                mac_address="AA:BB:CC:DD:EE:01",
                model="ESP32",
                esphome_version="2024.1.0",
            ),
        ],
    )

    result = validate_mappings(registry, scan)

    assert result.valid_count == 0
    assert len(result.unmapped_devices) == 1
    assert result.unmapped_devices[0] == ("esp-orphan", "192.168.1.10")
