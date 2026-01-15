"""Tests for internal modules."""

from __future__ import annotations

from datetime import datetime, timezone

from espro.config import ScanningConfig, Settings, load_settings, write_settings
from espro.core import validate_mappings
from espro.database import Database
from espro.models import DeviceRegistry, LogicalDevice, PhysicalDevice, ScanResult


def test_config_roundtrip(tmp_path):
    path = tmp_path / "config.toml"
    settings = Settings(scanning=ScanningConfig(default_network="10.0.0.0/24"))
    write_settings(settings, path)

    loaded = load_settings(path)
    assert loaded.scanning.default_network == "10.0.0.0/24"


def test_device_registry_crud(tmp_path):
    db = Database(tmp_path)

    db.add_logical_device("kitchen_light", "esp-kitchen.local", notes="Above sink")
    registry = db.load_devices()
    assert "kitchen_light" in registry.logical_devices
    assert registry.logical_devices["kitchen_light"].physical == "esp-kitchen.local"

    removed = db.remove_logical_device("kitchen_light")
    assert removed is True

    removed_again = db.remove_logical_device("kitchen_light")
    assert removed_again is False


def test_scan_roundtrip(tmp_path):
    db = Database(tmp_path)

    devices = [
        PhysicalDevice(
            ip="192.168.1.10",
            name="esp-test",
            friendly_name="Test Device",
            mac_address="AA:BB:CC:DD:EE:FF",
            model="ESP32",
            esphome_version="2024.1.0",
        )
    ]
    db.save_scan(devices, network="192.168.1.0/24")

    result = db.load_current_scan()
    assert result is not None
    assert len(result.devices) == 1
    assert result.devices[0].name == "esp-test"
    assert result.network == "192.168.1.0/24"


def test_validate_mappings_all_valid():
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
