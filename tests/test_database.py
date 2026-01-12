"""Tests for Database class."""

from espro.database import Database
from espro.models import EsProConfig, PhysicalDevice, ScanningConfig


def test_config_roundtrip(tmp_path):
    """Test config save and load."""
    db = Database(tmp_path)

    config = EsProConfig(scanning=ScanningConfig(default_network="10.0.0.0/24"))
    db.save_config(config)

    loaded = db.get_config()
    assert loaded.scanning.default_network == "10.0.0.0/24"


def test_device_registry_crud(tmp_path):
    """Test logical device add, get, remove."""
    db = Database(tmp_path)

    db.add_logical_device("kitchen_light", "esp-kitchen.local", notes="Above sink")
    registry = db.get_devices()
    assert "kitchen_light" in registry.logical_devices
    assert registry.logical_devices["kitchen_light"].physical == "esp-kitchen.local"

    removed = db.remove_logical_device("kitchen_light")
    assert removed is True

    removed_again = db.remove_logical_device("kitchen_light")
    assert removed_again is False


def test_scan_roundtrip(tmp_path):
    """Test scan save and load."""
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

    result = db.get_current_scan()
    assert result is not None
    assert len(result.devices) == 1
    assert result.devices[0].name == "esp-test"
    assert result.network == "192.168.1.0/24"
