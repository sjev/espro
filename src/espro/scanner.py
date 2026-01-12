"""Network scanning for ESPHome devices."""

import asyncio
import ipaddress
import logging
import socket
from dataclasses import dataclass
from typing import TYPE_CHECKING

import aioesphomeapi

if TYPE_CHECKING:
    from espro.models.device import PhysicalDevice

logger = logging.getLogger(__name__)


ESPHOME_PORT = 6053
DEFAULT_TIMEOUT = 5.0


@dataclass
class ESPHomeDevice:
    """Information about a discovered ESPHome device."""

    ip: str
    name: str
    friendly_name: str
    mac_address: str
    model: str
    esphome_version: str


async def check_device(
    ip: str, port: int = ESPHOME_PORT, timeout: float = DEFAULT_TIMEOUT
) -> ESPHomeDevice | None:
    """Check if an IP address has an ESPHome device and return its info."""
    logger.debug(f"Checking {ip}")
    try:
        api = aioesphomeapi.APIClient(ip, port=port, password="")
        await asyncio.wait_for(api.connect(login=True), timeout=timeout)
        info = await api.device_info()
        await api.disconnect()
        device = ESPHomeDevice(
            ip=ip,
            name=info.name,
            friendly_name=info.friendly_name,
            mac_address=info.mac_address,
            model=info.model,
            esphome_version=info.esphome_version,
        )
        logger.info(f"Found device '{device.name}' at {ip}")
        return device
    except (asyncio.TimeoutError, TimeoutError):
        logger.debug(f"No response from {ip} (timeout)")
        return None
    except Exception as e:
        logger.debug(f"Failed to connect to {ip}: {e}")
        return None


async def scan_network(
    network: str, port: int = ESPHOME_PORT, timeout: float = DEFAULT_TIMEOUT
) -> list[ESPHomeDevice]:
    """Scan a network range for ESPHome devices."""
    net = ipaddress.ip_network(network, strict=False)
    hosts = list(net.hosts())
    logger.debug(f"Scanning network {network} ({len(hosts)} hosts)")
    tasks = [check_device(str(ip), port, timeout) for ip in hosts]
    results = await asyncio.gather(*tasks)
    devices = [device for device in results if device is not None]
    logger.debug(f"Scan complete: found {len(devices)} devices")
    return devices


def detect_local_network() -> str:
    """Detect the local network CIDR (e.g., '192.168.1.0/24')."""
    try:
        # Connect to a public IP to determine local interface IP
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
        # Assume /24 subnet (most common for home networks)
        network = ipaddress.ip_network(f"{local_ip}/24", strict=False)
        logger.debug(f"Detected local network: {network}")
        return str(network)
    except OSError as e:
        raise RuntimeError("Could not detect local network") from e


def to_physical_device(device: ESPHomeDevice) -> "PhysicalDevice":
    """Convert ESPHomeDevice to PhysicalDevice model."""
    from espro.models.device import PhysicalDevice

    return PhysicalDevice(
        ip=device.ip,
        name=device.name,
        friendly_name=device.friendly_name,
        mac_address=device.mac_address,
        model=device.model,
        esphome_version=device.esphome_version,
    )
