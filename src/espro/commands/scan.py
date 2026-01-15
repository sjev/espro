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
    host_count: int
    if isinstance(net, ipaddress.IPv4Network):
        host_count = (
            int(net.num_addresses - 2)
            if net.prefixlen <= 30
            else int(net.num_addresses)
        )
    else:
        host_count = int(net.num_addresses)

    if host_count <= 0:
        logger.debug("Scanning network %s (no hosts)", network)
        return []

    worker_count = min(config.parallel_scans, host_count)
    logger.debug(
        "Scanning network %s (%d hosts, %d workers)", network, host_count, worker_count
    )

    queue: asyncio.Queue[str | None] = asyncio.Queue(maxsize=worker_count * 4)
    devices: list[PhysicalDevice] = []

    async def _producer() -> None:
        for host in net.hosts():
            await queue.put(str(host))
        for _ in range(worker_count):
            await queue.put(None)

    async def _worker() -> None:
        while True:
            host = await queue.get()
            try:
                if host is None:
                    return
                device = await check_device(host, config)
                if device is not None:
                    devices.append(device)
            finally:
                queue.task_done()

    workers = [asyncio.create_task(_worker()) for _ in range(worker_count)]
    workers_completed = False
    try:
        await _producer()
        await queue.join()
        await asyncio.gather(*workers)
        workers_completed = True
    finally:
        if not workers_completed:
            for worker in workers:
                if not worker.done():
                    worker.cancel()
            await asyncio.gather(*workers, return_exceptions=True)

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
