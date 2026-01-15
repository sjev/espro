from __future__ import annotations

from espro.models import DeviceRegistry, ScanResult, ValidationResult


def validate_mappings(registry: DeviceRegistry, scan: ScanResult) -> ValidationResult:
    physical_by_ip = {device.ip: device for device in scan.devices}
    physical_by_name = {device.name: device for device in scan.devices}

    errors: list[str] = []
    warnings: list[str] = []
    valid_count = 0
    matched_names: set[str] = set()

    for logical_name, logical_device in registry.logical_devices.items():
        physical_ref = logical_device.physical

        found = None
        matched_name = None

        if physical_ref in physical_by_ip:
            found = physical_by_ip[physical_ref]
            matched_name = found.name
        elif physical_ref in physical_by_name:
            found = physical_by_name[physical_ref]
            matched_name = physical_ref
        elif physical_ref.replace(".local", "") in physical_by_name:
            matched_name = physical_ref.replace(".local", "")
            found = physical_by_name[matched_name]

        if found:
            valid_count += 1
            if matched_name:
                matched_names.add(matched_name)
        else:
            errors.append(
                f"Logical device '{logical_name}' points to '{physical_ref}' "
                "which was not found in scan"
            )

    unmapped = [
        (device.name, device.ip)
        for device in scan.devices
        if device.name not in matched_names
    ]

    return ValidationResult(
        errors=errors,
        warnings=warnings,
        valid_count=valid_count,
        unmapped_devices=unmapped,
    )
