"""Business logic services."""

from dataclasses import dataclass

from espro.models import DeviceRegistry, ScanResult


@dataclass
class ValidationResult:
    """Result of validating logical devices against scan."""

    errors: list[str]
    warnings: list[str]
    valid_count: int
    unmapped_devices: list[tuple[str, str]]  # (name, ip)


def validate_mappings(registry: DeviceRegistry, scan: ScanResult) -> ValidationResult:
    """Validate logical device mappings against scan results.

    Returns ValidationResult with errors, warnings, and unmapped devices.
    """
    physical_by_ip = {d.ip: d for d in scan.devices}
    physical_by_name = {d.name: d for d in scan.devices}

    errors: list[str] = []
    warnings: list[str] = []
    valid_count = 0
    matched_names: set[str] = set()

    for logical_name, logical_device in registry.logical_devices.items():
        physical_ref = logical_device.physical

        # Check if it's an IP or hostname
        found = None
        matched_name = None

        if physical_ref in physical_by_ip:
            found = physical_by_ip[physical_ref]
            matched_name = found.name
        elif physical_ref in physical_by_name:
            found = physical_by_name[physical_ref]
            matched_name = physical_ref
        elif physical_ref.replace(".local", "") in physical_by_name:
            # Try without .local suffix
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

    # Find unmapped physical devices
    unmapped = [(d.name, d.ip) for d in scan.devices if d.name not in matched_names]

    return ValidationResult(
        errors=errors,
        warnings=warnings,
        valid_count=valid_count,
        unmapped_devices=unmapped,
    )
