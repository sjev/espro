from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ValidationResult:
    errors: list[str]
    warnings: list[str]
    valid_count: int
    unmapped_devices: list[tuple[str, str]]
