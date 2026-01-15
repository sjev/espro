from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Redactor:
    enabled: bool = True
    _mac_map: dict[str, int] = field(default_factory=dict)
    _mac_counter: int = 0

    def redact_ip(self, ip: str) -> str:
        if not self.enabled:
            return ip
        parts = ip.split(".")
        if len(parts) == 4 and all(part.isdigit() for part in parts):
            return f"x.x.x.{parts[3]}"
        return ip

    def redact_mac(self, mac: str) -> str:
        if not self.enabled:
            return mac
        parts = mac.split(":")
        if len(parts) != 6:
            return mac
        prefix = ":".join(parts[:3])
        counter = self._mac_map.get(mac)
        if counter is None:
            self._mac_counter += 1
            counter = self._mac_counter
            self._mac_map[mac] = counter
        return f"{prefix}:xx:xx:{counter:02d}"

    def redact_version(self, version: str | None) -> str:
        if not self.enabled:
            return "" if version is None else version
        if version is None or "." not in version:
            return "" if version is None else version
        major = version.split(".", 1)[0]
        return f"{major}.x"
