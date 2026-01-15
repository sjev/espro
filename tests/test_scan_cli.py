from __future__ import annotations

from typer.testing import CliRunner

import espro.cli.commands.scan as scan_cmd
from espro.cli.app import app
from espro.config import (
    DatabaseConfig,
    ScanningConfig,
    Settings,
    get_settings,
    write_settings,
)
from espro.database import Database
from espro.models import PhysicalDevice


def test_scan_shows_logical_name_for_ip_mapping(
    tmp_path,
    monkeypatch,
):
    data_dir = tmp_path / "data"
    config_path = tmp_path / "config.toml"
    write_settings(
        Settings(
            database=DatabaseConfig(path=str(data_dir)),
            scanning=ScanningConfig(default_network="192.168.1.0/24"),
        ),
        config_path,
    )
    monkeypatch.setenv("ESPRO_CONFIG", str(config_path))
    get_settings.cache_clear()

    db = Database(data_dir)
    db.add_logical_device("test-switch", "192.168.1.199")

    async def _fake_scan_network(_network: str, _config: ScanningConfig):
        return [
            PhysicalDevice(
                ip="192.168.1.199",
                name="soonoff-r3-b71cdb",
                friendly_name="Test Switch",
                mac_address="AA:BB:CC:DD:EE:FF",
                model="ESP32",
                esphome_version="2024.12.0",
            )
        ]

    monkeypatch.setattr(scan_cmd, "scan_network", _fake_scan_network)

    runner = CliRunner()
    result = runner.invoke(app, ["scan", "192.168.1.0/24"])
    assert result.exit_code == 0
    assert "test-switch" in result.stdout
