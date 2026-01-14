# What this library does

`aioesphomeapi` is an **async Python client** for ESPHome’s **Native API** (TCP port usually `6053`).
It lets you connect to an ESPHome device, fetch device/entity metadata, subscribe to state/log streams, and send commands (light/switch/climate/etc) and optional Bluetooth-proxy/voice-assistant features.

# Main objects and functions

## Connection / lifecycle
- **`APIClient`**: main high-level client; you create one per device and reuse it across reconnects.
- **`ReconnectLogic`**: background reconnection manager for an `APIClient` (recommended for long-lived integrations).

## Streaming helpers
- **`APIClient.subscribe_states(...)`**: subscribe to entity state updates.
- **`APIClient.subscribe_logs(...)`**: subscribe to device logs.
- **`LogParser` / `parse_log_message(...)`**: format ESPHome log lines (handles multi-line + ANSI color).

## Metadata / models (returned objects)
- **`DeviceInfo`**: device metadata (name, MAC, features, etc).
- **`EntityInfo`** + many subclasses (`LightInfo`, `SensorInfo`, …): metadata for each entity; includes the **`key`** you must use for commands.
- **`EntityState`** + many subclasses (`LightState`, `SensorState`, …): state updates.
- **`UserService`** / **`UserServiceArg`**: user-defined services exposed by the device.

## Errors (most common)
- **`APIConnectionError`** (base) and subclasses like `ResolveTimeoutAPIError`, `InvalidAuthAPIError`, `RequiresEncryptionAPIError`, `InvalidEncryptionKeyAPIError`, `SocketAPIError`, `TimeoutAPIError`, `PingFailedAPIError`, …
- Bluetooth-specific: `BluetoothGATTAPIError`, `BluetoothConnectionDroppedError`, plus `BLEConnectionError` enum and `ESP_CONNECTION_ERROR_DESCRIPTION`.

# How to use it

## Normal call flow (single session)

1) **Create client**
- `client = aioesphomeapi.APIClient(host, port, password=None, noise_psk=..., ...)`

2) **Connect + (optional) login/auth**
- `await client.connect(login=True)`
  - This resolves the host (mDNS/IP), opens the socket, performs protocol handshake, and authenticates.

3) **Fetch metadata** (usually once per connection)
- `device_info = await client.device_info()`
- `(entities, services) = await client.list_entities_services()`
  - Each `EntityInfo` has a **`key`** (and optionally `device_id`) used for commands.

4) **Subscribe** (optional, for streaming updates)
- `client.subscribe_states(on_state)`
- `unsub_logs = client.subscribe_logs(on_log, log_level=..., dump_config=...)`

5) **Send commands** (optional)
- Call `client.light_command(...)`, `client.switch_command(...)`, etc, using the entity `key`.

6) **Disconnect**
- `await client.disconnect()`

## Long-lived usage (recommended)

Use `ReconnectLogic` to keep the connection up and re-subscribe on reconnect:

- Create `APIClient`.
- Create `ReconnectLogic(client=..., on_connect=..., on_disconnect=...)`.
- `await logic.start()`.
- In `on_connect`, call `device_info()` / `list_entities_services()` and set up subscriptions.
- To stop reconnecting: `await logic.stop()` (does **not** automatically `disconnect()` the client; you decide how to tear down).

# API reference

## `APIClient`

### Constructor
**Purpose**: Configure a client for a target device.

**Signature** (from `APIClientBase.__init__`):
```python
APIClient(
  address: str,
  port: int,
  password: str | None,  # pass None for no password
  *,
  client_info: str = "aioesphomeapi",
  keepalive: float = 20.0,  # KEEP_ALIVE_FREQUENCY
  zeroconf_instance = None,
  noise_psk: str | None = None,
  expected_name: str | None = None,
  addresses: list[str] | None = None,
  expected_mac: str | None = None,
  timezone: str | None = None,
)
```

**Parameters**:
- `address`: hostname/IP (often `"name.local"` or an IP).
- `port`: usually `6053`.
- `password`: legacy password auth (ESPHome removed password auth in 2026.1.0; use `noise_psk` for modern devices).
- `noise_psk`: base64-like pre-shared key for Noise encryption (recommended).
- `addresses`: optional list of candidate IPs; overrides `address` for connection attempts.
- `expected_name`: if set, fails handshake if the device name differs (prevents connecting to wrong device after DHCP changes).
- `expected_mac`: if set, fails handshake if the device MAC differs (format: lowercase hex without separators, e.g. `"00aa22334455"`).
- `keepalive`: ping interval; used to detect dead connections.
- `zeroconf_instance`: provide an existing zeroconf instance if you manage one.
- `timezone`: IANA timezone name sent to the device (if not set, it auto-detects system timezone).

**Return**: `APIClient` instance.

**Errors**: none immediately; connection/auth errors occur during `connect`/handshake.

**Async or blocking**: constructor is synchronous.

**Side effects**: stores config; does not connect.

---

### `await connect(on_stop=None, login=False, log_errors=True) -> None`
**Purpose**: full connect sequence.

**Parameters**:
- `on_stop(expected_disconnect: bool)`: optional coroutine callback invoked when the connection stops.
- `login`: when `True`, performs authentication/login so requests/subscriptions are allowed.
- `log_errors`: whether the connection should log connection errors.

**Return**: `None`.

**Errors**:
- `APIConnectionError` and subclasses (resolve/handshake/auth/socket/timeouts).

**Async**: async.

**Side effects**:
- opens network connection; sets `client.api_version`; caches device name; creates internal `APIConnection`.

**Order constraints**:
- Must be called before any request/subscribe/command methods.

---

### Partial connection steps
These are primarily for advanced reconnection flows (used by `ReconnectLogic`).

- `await start_resolve_host(on_stop=None, log_errors=True) -> None`
- `await start_connection() -> None`
- `await finish_connection(login=False) -> None`

**Order**: `start_resolve_host()` → `start_connection()` → `finish_connection(login=...)`.

---

### `await disconnect(force: bool = False) -> None`
**Purpose**: close the connection.

**Parameters**:
- `force`: if `True`, forcibly closes underlying transport; otherwise attempts a graceful disconnect.

**Return**: `None`.

**Errors**: may raise `APIConnectionError` subclasses if disconnect fails.

**Async**: async.

**Side effects**: stops message callbacks; clears internal connection and cached device info.

---

### Metadata

#### `await device_info() -> DeviceInfo`
**Purpose**: fetch device metadata.

**Return**: `DeviceInfo` model.

**Errors**: `APIConnectionError` subclasses; `TimeoutAPIError`.

**Async**: async.

**Side effects**: caches device info on the client and updates cached device name.

#### `await list_entities_services() -> tuple[list[EntityInfo], list[UserService]]`
**Purpose**: fetch all entity metadata and user services.

**Return**:
- `entities`: list of `EntityInfo` subclasses (light/sensor/etc).
- `services`: list of `UserService`.

**Errors**: `APIConnectionError` subclasses; `TimeoutAPIError`.

**Async**: async.

**Side effects**:
- may call `device_info_and_list_entities()` internally if device info isn’t cached.

#### `await device_info_and_list_entities() -> tuple[DeviceInfo, list[EntityInfo], list[UserService]]`
**Purpose**: fetch device info + entities/services in one network round-trip.

---

### Subscriptions (streaming)

#### `subscribe_states(on_state: Callable[[EntityState], None]) -> None`
**Purpose**: stream entity state changes.

**Parameters**:
- `on_state(state)`: called for each `EntityState` update (subclass depends on entity).

**Return**: `None` (no unsubscribe handle for this method).

**Errors**: raises `APIConnectionError` immediately if not connected.

**Async**: non-async (registers callbacks and sends subscription request).

**Side effects**: device starts sending state updates.

**Gotcha**: because no unsubscribe is returned, you typically rely on disconnect/reconnect boundaries.

#### `subscribe_logs(on_log, log_level=None, dump_config=None) -> Callable[[], None]`
**Purpose**: stream device logs.

**Parameters**:
- `on_log(msg: SubscribeLogsResponse)`: raw protobuf log message callback.
- `log_level`: `LogLevel` enum or `None`.
- `dump_config`: `bool` or `None`.

**Return**: `unsub()` callback that removes local callbacks.

**Errors**: `APIConnectionError` if not connected.

**Async**: non-async.

**Side effects**:
- device will keep sending logs until you also set `log_level=LogLevel.LOG_LEVEL_NONE` and unsubscribe.

#### `subscribe_service_calls(on_service_call: Callable[[HomeassistantServiceCall], None]) -> None`
**Purpose**: receive Home Assistant service call requests originating from the device.

---

### Commands (send-only)
All commands are **non-async** and send a message; success/failure is generally not confirmed (unless documented otherwise).

Common parameters:
- `key: int`: entity key from `EntityInfo.key`.
- `device_id: int = 0`: sub-device identifier; use `EntityInfo.device_id` when present.

Key command methods:
- `cover_command(key, position=None, tilt=None, stop=False, device_id=0) -> None`
- `fan_command(key, state=None, speed=None, speed_level=None, oscillating=None, direction=None, preset_mode=None, device_id=0) -> None`
- `light_command(key, state=None, brightness=None, color_mode=None, color_brightness=None, rgb=None, white=None, color_temperature=None, cold_white=None, warm_white=None, transition_length=None, flash_length=None, effect=None, device_id=0) -> None`
  - `transition_length` / `flash_length` are **seconds** (converted to ms internally).
- `switch_command(key, state: bool, device_id=0) -> None`
- `climate_command(key, mode=None, target_temperature=None, target_temperature_low=None, target_temperature_high=None, fan_mode=None, swing_mode=None, custom_fan_mode=None, preset=None, custom_preset=None, target_humidity=None, device_id=0) -> None`
- `number_command(key, state: float, device_id=0) -> None`
- `date_command(key, year, month, day, device_id=0) -> None`
- `time_command(key, hour, minute, second, device_id=0) -> None`
- `datetime_command(key, epoch_seconds: int, device_id=0) -> None`
- `select_command(key, state: str, device_id=0) -> None`
- `siren_command(key, state=None, tone=None, volume=None, duration=None, device_id=0) -> None`
- `button_command(key, device_id=0) -> None`
- `lock_command(key, command: LockCommand, code=None, device_id=0) -> None`
- `valve_command(key, position=None, stop=False, device_id=0) -> None`
- `water_heater_command(key, *, mode=None, target_temperature=None, target_temperature_low=None, target_temperature_high=None, away=None, on=None, device_id=0) -> None`
- `media_player_command(key, *, command=None, volume=None, media_url=None, announcement=None, device_id=0) -> None`
- `text_command(key, state: str, device_id=0) -> None`
- `update_command(key, command: UpdateCommand, device_id=0) -> None`

**Errors**:
- `APIConnectionError` if not connected or connection not ready.
- Underlying socket may close and raise `SocketClosedAPIError`.

---

### User services

#### `await execute_service(service: UserService, data: dict[str, ...], *, return_response=None, timeout=30.0) -> ExecuteServiceResponse | None`
**Purpose**: call a device-defined service.

**Parameters**:
- `service`: a `UserService` from `list_entities_services()`.
- `data`: dict mapping each `UserServiceArg.name` to a value matching its type.
  - Types: `bool`, `int`, `float`, `str`, or lists of those (arrays).
- `return_response`:
  - `None` (default): don’t request a response; returns `None`.
  - `True/False`: request a response (device dependent); returns `ExecuteServiceResponse | None`.
- `timeout`: seconds to wait when requesting a response.

**Return**:
- `None` if `return_response is None`.
- Otherwise an `ExecuteServiceResponse` model (or `None` if device sends none).

**Errors**:
- `KeyError` if `data` is missing required keys (the code indexes `data[arg.name]`).
- `TimeoutAPIError` if response was requested and not received in time.
- `APIConnectionError` subclasses.

---

### Camera
- `request_single_image() -> None`
- `request_image_stream() -> None`

These send `CameraImageRequest`; you must separately subscribe to the relevant messages (state subscription includes `CameraImageResponse`).

---

### Bluetooth proxy (optional; device must support it)

#### `subscribe_bluetooth_le_advertisements(on_advertisement) -> Callable[[], None]`
- Callback receives `BluetoothLEAdvertisement` (model).

#### `subscribe_bluetooth_le_raw_advertisements(on_advertisements) -> Callable[[], None]`
- Callback receives `BluetoothLERawAdvertisementsResponse` (protobuf).

#### `await bluetooth_device_connect(address, on_bluetooth_connection_state, *, timeout=30.0, disconnect_timeout=20.0, feature_flags=0, has_cache=False, address_type: int) -> Callable[[], None]`
- **`address`**: integer MAC (as used by ESPHome API).
- **`address_type` is required**; missing it raises `ValueError`.
- Returns `unsub()` callback to stop receiving connection-state callbacks.

#### GATT
- `await bluetooth_gatt_get_services(address) -> ESPHomeBluetoothGATTServices`
- `await bluetooth_gatt_read(address, handle, timeout=...) -> bytearray`
- `await bluetooth_gatt_read_descriptor(address, handle, timeout=...) -> bytearray`
- `await bluetooth_gatt_write(address, handle, data: bytes, response: bool, timeout=...) -> None`
- `await bluetooth_gatt_write_descriptor(address, handle, data: bytes, timeout=..., wait_for_response=True) -> None`
- `await bluetooth_gatt_start_notify(address, handle, on_notify, timeout=10.0) -> (stop_notify_async, remove_callback)`

**Errors**:
- `BluetoothGATTAPIError` if ESPHome returns a GATT error.
- `BluetoothConnectionDroppedError` if the peripheral connection state changes while waiting.
- `TimeoutAPIError`.
- `ValueError` if device is too old / missing required features.

---

### Voice assistant (optional)

- `subscribe_voice_assistant(handle_start=..., handle_stop=..., handle_audio=None, handle_announcement_finished=None) -> Callable[[], None]`
- `send_voice_assistant_event(event_type, data: dict[str,str] | None) -> None`
- `send_voice_assistant_audio(data: bytes) -> None`
- `send_voice_assistant_timer_event(...) -> None`
- `await send_voice_assistant_announcement_await_response(media_id, timeout, text="", preannounce_media_id="", start_conversation=False) -> VoiceAssistantAnnounceFinished`
- `await get_voice_assistant_configuration(timeout, external_wake_words=None) -> VoiceAssistantConfigurationResponse`
- `set_voice_assistant_configuration(active_wake_words: list[str]) -> None`

**Unknowns**: exact semantics depend on the device firmware’s supported feature flags.

---

## `ReconnectLogic`

### `ReconnectLogic(client, on_connect, on_disconnect, zeroconf_instance=None, name=None, on_connect_error=None)`
**Purpose**: keep an `APIClient` connected with backoff + zeroconf triggers.

**Parameters**:
- `client`: an `APIClient` instance.
- `on_connect`: async callback invoked after a successful handshake/login.
- `on_disconnect(expected_disconnect: bool)`: async callback invoked when disconnected.
- `on_connect_error(err)`: optional async callback invoked on failed connect attempt.
- `name`: optional device name used for zeroconf listening.

### `await start() -> None`
Starts background reconnection attempts.

### `await stop() -> None`
Stops reconnecting and closes the internal zeroconf manager.

**Errors**: user callbacks may raise; connect errors are handled internally but delivered to `on_connect_error`.

**Async**: both methods are async.

**Side effects**: schedules background tasks/timers; performs network connects.

## `LogParser`

### `LogParser(strip_ansi_escapes: bool = False)`
**Purpose**: stateful, line-by-line log formatter (keeps prefix/color for continuation lines).

### `parse_line(line: str, timestamp: str) -> str`
**Return**: formatted line (may be `""` for empty/whitespace-only lines).

**Errors**: none expected for normal strings.

## `parse_log_message(text: str, timestamp: str, *, strip_ansi_escapes: bool = False) -> Iterable[str]`
**Purpose**: stateless formatter for a whole log message (possibly multi-line).

**Return**: iterable of formatted lines.

---

## `wifi_mac_to_bluetooth_mac(wifi_mac: str) -> str`
**Purpose**: convert ESP32 base WiFi MAC to derived Bluetooth MAC.

**Errors**: raises `ValueError` for invalid MAC string.

# Data structures

This library returns many model types; these are the ones you typically must understand to call methods.

## `DeviceInfo`
Fields (common):
- `name: str` (device name)
- `mac_address: str` (format depends on firmware)
- `esphome_version: str`
- `bluetooth_proxy_feature_flags: int`
- `voice_assistant_feature_flags: int`
- `api_encryption_supported: bool`
- `devices: list[SubDeviceInfo]` (for multi-device setups)
- `areas: list[AreaInfo]`

## `EntityInfo` (base)
Fields:
- `key: int` **(required for commands)**
- `object_id: str` (may be empty for some API versions; the client may fill it in)
- `name: str`
- `device_id: int` (0 for main device; non-zero for sub-devices)

Many subclasses add extra fields (e.g., `LightInfo`, `ClimateInfo`).

## `EntityState` (base)
Fields:
- `key: int` (matches an `EntityInfo.key`)
- `device_id: int`

Subclasses include the actual state (e.g., `SensorState.state: float`, `SwitchState.state: bool`, etc.).

## `UserService`
Fields:
- `name: str`
- `key: int`
- `args: list[UserServiceArg]`
- `supports_response: SupportsResponseType | None`

## `UserServiceArg`
Fields:
- `name: str`
- `type: UserServiceArgType | None` (`BOOL`, `INT`, `FLOAT`, `STRING`, or arrays)

## `ExecuteServiceResponse`
Fields:
- `call_id: int`
- `success: bool`
- `error_message: str`
- `response_data: bytes` (JSON payload from ESPHome)

## `BluetoothLEAdvertisement`
Fields:
- `address: int` (integer MAC)
- `address_type: int`
- `rssi: int`
- `name: str`
- `service_uuids: list[str]`
- `service_data: dict[str, bytes]`
- `manufacturer_data: dict[int, bytes]`

# Examples

## Normal usage
```python
import asyncio
import aioesphomeapi

async def main() -> None:
    api = aioesphomeapi.APIClient(
        "my-node.local",
        6053,
        password=None,
        noise_psk="YOUR_NOISE_PSK",  # omit if device is plaintext (not recommended)
        expected_name="my-node",     # optional safety check
    )

    await api.connect(login=True)

    info = await api.device_info()
    entities, services = await api.list_entities_services()

    # Pick a switch entity key
    switch = next(e for e in entities if type(e).__name__ == "SwitchInfo")
    api.switch_command(switch.key, True, device_id=switch.device_id)

    def on_state(state: aioesphomeapi.EntityState) -> None:
        print("STATE:", state)

    api.subscribe_states(on_state)

    # keep running briefly
    await asyncio.sleep(5)
    await api.disconnect()

asyncio.run(main())
```

## One failing case (not connected)
```python
import aioesphomeapi

api = aioesphomeapi.APIClient("my-node.local", 6053, password=None)

try:
    # No connect() yet
    api.switch_command(key=1, state=True)
except aioesphomeapi.APIConnectionError as e:
    print("Expected failure:", e)
```

# Gotchas

- **You must `await connect(login=True)` before calling request/subscribe/command methods**; otherwise you get `APIConnectionError`.
- `subscribe_states()` does **not** return an unsubscribe function; design your code around disconnect/reconnect boundaries.
- `subscribe_logs()`’s returned `unsub()` only removes local callbacks; the device may still keep sending logs unless you also set `log_level=LOG_LEVEL_NONE`.
- `execute_service()` will raise **`KeyError`** if your `data` dict is missing any required arg names.
- Bluetooth proxy APIs require firmware support; `bluetooth_device_connect()` can raise `ValueError` if the device lacks required features, and it **requires** `address_type`.
- Callbacks run on the event loop thread; do not block. If you need async work, create a task.

# Unknowns

- The repository exports many model classes via `from .model import *`; this guide lists only the ones most callers need. For entity-specific fields/states (e.g. `LightState`, `ClimateState`), you must inspect `aioesphomeapi.model`.
- Some features (voice assistant, bluetooth proxy, Z-Wave proxy) depend on device firmware flags; the exact supported behaviors are not fully specified here.
