from __future__ import annotations

import json
import tomllib
from datetime import datetime, timezone
from pathlib import Path

from pydantic import ValidationError

from espro.models import DeviceRegistry, LogicalDevice, PhysicalDevice, ScanResult

DEVICES_FILE = "devices.toml"
PHYSICAL_DIR = "physical"
CURRENT_SCAN_FILE = "current.json"


def _toml_string(value: str) -> str:
    return json.dumps(value)


def _render_devices_toml(registry: DeviceRegistry) -> str:
    lines = [
        "# ESPro Logical Device Registry",
        "# Maps friendly logical names to physical ESPHome devices",
        "",
        "[logical_devices]",
    ]

    for name, device in sorted(registry.logical_devices.items()):
        fields = [f"physical = {_toml_string(device.physical)}"]
        if device.notes:
            fields.append(f"notes = {_toml_string(device.notes)}")
        lines.append(f"{_toml_string(name)} = {{ {', '.join(fields)} }}")

    lines.append("")
    return "\n".join(lines)


class Database:
    def __init__(self, data_dir: Path) -> None:
        self._data_dir = data_dir
        self._physical_dir = data_dir / PHYSICAL_DIR
        self._devices_path = data_dir / DEVICES_FILE
        self._current_scan_path = self._physical_dir / CURRENT_SCAN_FILE

    @property
    def path(self) -> Path:
        return self._data_dir

    @property
    def devices_path(self) -> Path:
        return self._devices_path

    @property
    def current_scan_path(self) -> Path:
        return self._current_scan_path

    def ensure_dirs(self) -> None:
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._physical_dir.mkdir(parents=True, exist_ok=True)

    def load_devices(self) -> DeviceRegistry:
        if not self._devices_path.exists():
            return DeviceRegistry()

        try:
            with self._devices_path.open("rb") as handle:
                data = tomllib.load(handle) or {}
        except tomllib.TOMLDecodeError as exc:
            raise ValueError(
                f"Invalid TOML in devices file: {self._devices_path}\\n{exc}"
            ) from exc

        logical_devices = data.get("logical_devices", {})

        try:
            return DeviceRegistry.model_validate({"logical_devices": logical_devices})
        except ValidationError as exc:
            raise ValueError(
                f"Invalid devices file: {self._devices_path}\n{exc}"
            ) from exc

    def save_devices(self, registry: DeviceRegistry) -> None:
        self.ensure_dirs()
        self._devices_path.write_text(_render_devices_toml(registry))

    def add_logical_device(
        self, name: str, physical: str, notes: str | None = None
    ) -> None:
        registry = self.load_devices()
        registry.logical_devices[name] = LogicalDevice(physical=physical, notes=notes)
        self.save_devices(registry)

    def remove_logical_device(self, name: str) -> bool:
        registry = self.load_devices()
        if name in registry.logical_devices:
            del registry.logical_devices[name]
            self.save_devices(registry)
            return True
        return False

    def save_scan(self, devices: list[PhysicalDevice], network: str) -> None:
        scan = ScanResult(
            scan_timestamp=datetime.now(timezone.utc),
            network=network,
            devices=devices,
        )

        self._physical_dir.mkdir(parents=True, exist_ok=True)
        with self._current_scan_path.open("w") as handle:
            json.dump(scan.model_dump(mode="json"), handle, indent=2)

    def load_current_scan(self) -> ScanResult | None:
        if not self._current_scan_path.exists():
            return None

        with self._current_scan_path.open("r") as handle:
            data = json.load(handle)

        return ScanResult.model_validate(data)

    def init(self) -> None:
        self.ensure_dirs()
        if not self._devices_path.exists():
            self.save_devices(DeviceRegistry())
