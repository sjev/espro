from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from espro.config import ScanningConfig
from espro.core import scanner as scan_module


def test_check_device_disables_aioesphomeapi_log_errors(
    monkeypatch: pytest.MonkeyPatch,
):
    created: list[DummyAPIClient] = []

    class DummyAPIClient:
        def __init__(self, host: str, port: int, password: str) -> None:
            self.host = host
            self.port = port
            self.password = password
            self.connect_kwargs: dict[str, object] | None = None

        async def connect(
            self, on_stop=None, login: bool = False, log_errors: bool = True
        ) -> None:
            self.connect_kwargs = {
                "on_stop": on_stop,
                "login": login,
                "log_errors": log_errors,
            }

        async def device_info(self):
            return SimpleNamespace(
                name="esp-test",
                friendly_name="Test Device",
                mac_address="AA:BB:CC:DD:EE:FF",
                model="ESP32",
                esphome_version="2024.1.0",
            )

        async def disconnect(self) -> None:
            return None

    def _factory(host: str, port: int, password: str) -> DummyAPIClient:
        client = DummyAPIClient(host, port, password)
        created.append(client)
        return client

    monkeypatch.setattr(scan_module.aioesphomeapi, "APIClient", _factory)

    config = ScanningConfig(timeout=0.1)
    device = asyncio.run(scan_module.check_device("192.168.1.123", config))
    assert device is not None

    assert created[0].connect_kwargs is not None
    assert created[0].connect_kwargs["log_errors"] is False
