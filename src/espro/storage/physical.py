"""Physical device storage."""

import json
from datetime import datetime, timezone
from pathlib import Path

from espro.models.device import PhysicalDevice, ScanResult


class PhysicalDeviceStorage:
    """Storage for physical device scan results."""

    def __init__(self, physical_dir: Path) -> None:
        self.physical_dir = physical_dir
        self.current_path = physical_dir / "current.json"

    def save_scan(self, devices: list[PhysicalDevice], network: str) -> None:
        """Save scan results to current.json."""
        scan = ScanResult(
            scan_timestamp=datetime.now(timezone.utc),
            network=network,
            devices=devices,
        )

        self.physical_dir.mkdir(parents=True, exist_ok=True)
        with open(self.current_path, "w") as f:
            json.dump(scan.model_dump(mode="json"), f, indent=2)

    def load_current(self) -> ScanResult | None:
        """Load current scan results."""
        if not self.current_path.exists():
            return None

        with open(self.current_path) as f:
            data = json.load(f)

        return ScanResult.model_validate(data)
