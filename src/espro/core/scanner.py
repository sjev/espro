from __future__ import annotations

import asyncio
import ipaddress
import logging
import socket
import string
import threading

import aioesphomeapi
from zeroconf import ServiceBrowser, ServiceInfo, ServiceListener, Zeroconf

from espro.config import ScanningConfig
from espro.models import PhysicalDevice

logger = logging.getLogger(__name__)

MDNS_SERVICE_TYPE = "_esphomelib._tcp.local."


def _decode_txt_properties(properties: dict[bytes, bytes | None]) -> dict[str, str]:
    decoded: dict[str, str] = {}
    for key, value in properties.items():
        key_text = key.decode("utf-8", errors="replace")
        if value is None:
            value_text = ""
        elif isinstance(value, bytes):
            value_text = value.decode("utf-8", errors="replace")
        else:
            value_text = str(value)
        decoded[key_text] = value_text
    return decoded


def _normalize_mac(value: str) -> str:
    if not value:
        return ""
    cleaned = value.replace(":", "").replace("-", "").replace(".", "")
    if len(cleaned) == 12 and all(ch in string.hexdigits for ch in cleaned):
        pairs = [cleaned[i : i + 2] for i in range(0, 12, 2)]
        return ":".join(pair.upper() for pair in pairs)
    return value


def _pick_ip(info: ServiceInfo) -> str | None:
    addresses = info.parsed_addresses()
    if not addresses:
        return None
    for address in addresses:
        if ":" not in address:
            return address
    return addresses[0]


def _strip_service_suffix(name: str) -> str:
    suffix = f".{MDNS_SERVICE_TYPE}"
    if name.endswith(suffix):
        return name[: -len(suffix)]
    return name.rstrip(".")


def _strip_local_suffix(hostname: str) -> str:
    cleaned = hostname.rstrip(".")
    if cleaned.endswith(".local"):
        return cleaned[: -len(".local")]
    return cleaned


def _device_from_service_info(
    info: ServiceInfo, service_name: str
) -> PhysicalDevice | None:
    ip = _pick_ip(info)
    if ip is None:
        return None

    properties = _decode_txt_properties(info.properties)
    name = _strip_service_suffix(service_name)
    if not name and info.server:
        name = _strip_local_suffix(info.server)

    friendly_name = properties.get("friendly_name", "")
    mac_address = _normalize_mac(
        properties.get("mac", "") or properties.get("mac_address", "")
    )
    model = (
        properties.get("model")
        or properties.get("platform")
        or properties.get("board")
        or ""
    )
    version = properties.get("version") or properties.get("esphome_version") or ""

    return PhysicalDevice(
        ip=ip,
        name=name or ip,
        friendly_name=friendly_name,
        mac_address=mac_address,
        model=model,
        esphome_version=version,
        port=info.port,
        txt=properties,
    )


class ESPHomeListener(ServiceListener):
    def __init__(self, info_timeout: float) -> None:
        self._info_timeout_ms = max(int(info_timeout * 1000), 1)
        self._lock = threading.Lock()
        self._found: dict[str, PhysicalDevice] = {}

    def add_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        info = zc.get_service_info(type_, name, timeout=self._info_timeout_ms)
        if not info:
            return
        device = _device_from_service_info(info, name)
        if device is None:
            return
        with self._lock:
            self._found[name] = device
        logger.debug("Discovered device '%s' at %s via mDNS", device.name, device.ip)

    def update_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        self.add_service(zc, type_, name)

    def remove_service(self, _zc: Zeroconf, _type_: str, name: str) -> None:
        with self._lock:
            self._found.pop(name, None)

    def devices(self) -> list[PhysicalDevice]:
        with self._lock:
            return list(self._found.values())


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
        logger.debug("Found device '%s' at %s", device.name, ip)
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
    logger.debug(
        "Discovering ESPHome devices via mDNS (timeout=%.2fs, label=%s)",
        config.timeout,
        network,
    )
    zeroconf = Zeroconf()
    listener = ESPHomeListener(config.timeout)
    ServiceBrowser(zeroconf, MDNS_SERVICE_TYPE, listener)
    try:
        await asyncio.sleep(config.timeout)
    finally:
        await asyncio.to_thread(zeroconf.close)

    devices = listener.devices()
    devices.sort(key=lambda device: (device.name, device.ip))
    logger.debug("mDNS scan complete: found %d devices", len(devices))
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
