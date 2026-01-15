from __future__ import annotations

import asyncio
import ipaddress
import logging
import socket

import aioesphomeapi

from espro.config import ScanningConfig
from espro.models import PhysicalDevice

logger = logging.getLogger(__name__)


async def check_device(ip: str, config: ScanningConfig) -> PhysicalDevice | None:
    logger.debug("Checking %s", ip)
    try:
        api = aioesphomeapi.APIClient(ip, port=config.port, password="")
        await asyncio.wait_for(
            api.connect(login=True, log_errors=False),
            timeout=config.timeout,
        )
        info = await api.device_info()
        await api.disconnect()
        device = PhysicalDevice(
            ip=ip,
            name=info.name,
            friendly_name=info.friendly_name,
            mac_address=info.mac_address,
            model=info.model,
            esphome_version=info.esphome_version,
        )
        logger.info("Found device '%s' at %s", device.name, ip)
        return device
    except (asyncio.TimeoutError, TimeoutError):
        logger.debug("No response from %s (timeout)", ip)
        return None
    except (
        aioesphomeapi.APIConnectionError,
        aioesphomeapi.InvalidAuthAPIError,
        ConnectionError,
        OSError,
    ) as exc:
        logger.debug("Failed to connect to %s: %s", ip, exc)
        return None


async def scan_network(network: str, config: ScanningConfig) -> list[PhysicalDevice]:
    net = ipaddress.ip_network(network, strict=False)
    hosts = [str(host) for host in net.hosts()]
    logger.debug("Scanning network %s (%d hosts)", network, len(hosts))

    semaphore = asyncio.Semaphore(config.parallel_scans)

    async def _bounded_check(host: str) -> PhysicalDevice | None:
        async with semaphore:
            return await check_device(host, config)

    tasks = [asyncio.create_task(_bounded_check(host)) for host in hosts]
    results = await asyncio.gather(*tasks)
    devices = [device for device in results if device is not None]
    logger.debug("Scan complete: found %d devices", len(devices))
    return devices


def detect_local_network() -> str:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            local_ip = sock.getsockname()[0]
        network = ipaddress.ip_network(f"{local_ip}/24", strict=False)
        logger.debug("Detected local network: %s", network)
        return str(network)
    except OSError as exc:
        raise RuntimeError("Could not detect local network") from exc
