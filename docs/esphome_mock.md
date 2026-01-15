# ESPHome Native API mock device (minimal switch)

This document captures the protocol details needed to build a **minimal mock ESPHome device** that can be used with `aioesphomeapi` (and therefore ESPro) without real hardware.

Primary sources (cloned in this repo under `/.vendor/`):
- `/.vendor/esphome/esphome/components/api/api.proto` (authoritative message definitions and framing notes)
- `/.vendor/aioesphomeapi/aioesphomeapi/connection.py` (actual client handshake/login behavior)
- `/.vendor/aioesphomeapi/aioesphomeapi/_frame_helper/plain_text.py` and `/.vendor/aioesphomeapi/aioesphomeapi/_frame_helper/packets.py` (plaintext framing implementation)
- `/.vendor/aioesphomeapi/aioesphomeapi/core.py` (message-id ↔ protobuf-class mapping used by the client)

## Scope / goal

Implement a mock TCP server (usually on port `6053`) that supports:
- Connecting from `aioesphomeapi.APIClient(...).connect(login=True)`
- `device_info()` returning realistic metadata (enough for ESPro’s `src/espro/scanner.py`)
- A single **switch entity** via `list_entities_services()`
- Commands and state updates:
  - receive `switch_command`
  - broadcast `switch` state via `subscribe_states`
- Keepalive (`ping`/`pong`)
- Graceful disconnect

No Noise encryption support is required for the *simplest* mock; use plaintext.

## Transport framing (plaintext)

ESPHome Native API frames are **length-delimited protobuf messages** over TCP.

From `/.vendor/esphome/esphome/components/api/api.proto`:
- Each frame is:
  1) **preamble** byte `0x00` (plaintext)
  2) **VarInt** message payload length in bytes (protobuf-encoded message only; **type not included**)
  3) **VarInt** message type id (numeric id from `option (id) = ...`)
  4) **payload bytes** (protobuf binary)

`aioesphomeapi`’s plaintext writer confirms this layout: `/.vendor/aioesphomeapi/aioesphomeapi/_frame_helper/packets.py`.

### VarInt (varuint) encoding/decoding

`aioesphomeapi` uses unsigned varints for framing (`_read_varuint` in `/.vendor/aioesphomeapi/aioesphomeapi/_frame_helper/plain_text.py`):
- 7-bit groups (LSB first), continue bit `0x80`.
- Decode until a byte with `(b & 0x80) == 0`.

### Multiple frames

Frames can be concatenated; you must parse in a loop and handle partial frames (TCP is a stream).

## Message ids you must implement (minimal switch device)

These ids are stable because they’re declared in `api.proto` and mirrored in `aioesphomeapi.core.MESSAGE_TYPE_TO_PROTO` (`/.vendor/aioesphomeapi/aioesphomeapi/core.py`).

**Base / lifecycle**
- `1` `HelloRequest` (client → server)
- `2` `HelloResponse` (server → client)
- `5` `DisconnectRequest` (both)
- `6` `DisconnectResponse` (both)
- `7` `PingRequest` (both)
- `8` `PingResponse` (both)

**Metadata**
- `9` `DeviceInfoRequest` (client → server)
- `10` `DeviceInfoResponse` (server → client)

**Entities**
- `11` `ListEntitiesRequest` (client → server)
- `17` `ListEntitiesSwitchResponse` (server → client)
- `19` `ListEntitiesDoneResponse` (server → client)

**State streaming**
- `20` `SubscribeStatesRequest` (client → server)
- `26` `SwitchStateResponse` (server → client)

**Commands**
- `33` `SwitchCommandRequest` (client → server)

**Optional (login/auth)**
- `3` `AuthenticationRequest` (client → server)
- `4` `AuthenticationResponse` (server → client)

Notes:
- `aioesphomeapi` can send `AuthenticationRequest` during `connect(login=True)` when `password is not None` (even though password auth is deprecated/removed in newer ESPHome). See `/.vendor/aioesphomeapi/aioesphomeapi/connection.py:_connect_hello_login`.
- The client does **not** wait for `AuthenticationResponse`; if you implement it, do not set `invalid_password=true` unless you want the client to treat it as fatal.

## Required connection flow (as `aioesphomeapi` performs it)

### 1) TCP connect + frame helper “handshake”

For plaintext, there is no cryptographic handshake; `aioesphomeapi` considers the transport ready immediately on `connection_made` (`APIPlaintextFrameHelper.ready_future` is completed).

### 2) Hello (+ optional auth)

`aioesphomeapi` sends:
- `HelloRequest` (type `1`)
- and, if `login=True`, an `AuthenticationRequest` (type `3`) may be sent **in the same write batch**.

Your mock server should respond with `HelloResponse` (type `2`) promptly.

Important details:
- `aioesphomeapi` currently sends `api_version_major=1, api_version_minor=14` in `HelloRequest` (`make_hello_request` in `/.vendor/aioesphomeapi/aioesphomeapi/connection.py`).
- Client accepts `api_version_major <= 2`; otherwise it fails.
- If the client was configured with `expected_name`, it will compare it to `HelloResponse.name` and fail on mismatch.

### 3) Keepalive

The client periodically sends `PingRequest` (type `7`). If you don’t answer with `PingResponse` (type `8`), the client will eventually close the connection (see keepalive timers in `/.vendor/aioesphomeapi/aioesphomeapi/connection.py`).

## Device info (what ESPro currently needs)

ESPro scanning (`src/espro/scanner.py`) calls `device_info()` and reads these fields:
- `name`
- `friendly_name`
- `mac_address`
- `model`
- `esphome_version`

Those come from `DeviceInfoResponse` (type `10`), defined in `api.proto` (see `message DeviceInfoResponse`).

Minimal practical `DeviceInfoResponse` contents:
- `name`: e.g. `"mock-switch-1"`
- `friendly_name`: e.g. `"Mock Switch 1"`
- `mac_address`: e.g. `"AA:BB:CC:DD:EE:FF"`
- `model`: e.g. `"ESP32"`
- `esphome_version`: e.g. `"2024.12.0"`
- Optionally set `api_encryption_supported=false` (default)

## Entities: one switch

When the client calls `list_entities_services()`, it sends `ListEntitiesRequest` (type `11`) and expects:
1) one or more `ListEntities*Response` messages
2) then `ListEntitiesDoneResponse` (type `19`)

For a single switch entity, respond with:
- `ListEntitiesSwitchResponse` (type `17`)
- `ListEntitiesDoneResponse` (type `19`)

From `api.proto` (`message ListEntitiesSwitchResponse`):
- `object_id` (string): stable id, e.g. `"relay"`
- `key` (fixed32): numeric entity key, e.g. `1` (must match state/commands)
- `name` (string): friendly entity name, e.g. `"Relay"`
- `assumed_state` (bool): typically `false`
- `device_id` (uint32): `0` for main device (unless you emulate sub-devices)

## State subscription and updates

When the client calls `subscribe_states(...)`, it sends `SubscribeStatesRequest` (type `20`) and then expects state updates.

For a switch:
- Send `SwitchStateResponse` (type `26`) with:
  - `key`: your switch key (e.g. `1`)
  - `state`: current boolean state
  - `device_id`: `0`

Recommended behavior:
- After receiving `SubscribeStatesRequest`, immediately send an initial `SwitchStateResponse` so the client sees the current state.
- When the state changes, broadcast a `SwitchStateResponse` to all subscribed clients.

## Switch commands

When the client wants to change the switch, it sends `SwitchCommandRequest` (type `33`):
- `key`: the entity key
- `state`: desired boolean state
- `device_id`: `0`

Recommended behavior:
- Validate `key` (ignore unknown keys).
- Update internal state.
- Emit a `SwitchStateResponse` reflecting the new state (so subscribers get the change).

## Disconnect

Handle:
- `DisconnectRequest` (type `5`) → respond with `DisconnectResponse` (type `6`) and close the socket.

## Implementation notes (pragmatic choices)

### Use `aioesphomeapi`’s generated protobuf classes

For a mock, the easiest path is to **reuse the exact protobuf classes** that `aioesphomeapi` uses (import `aioesphomeapi.api_pb2`), and serialize with `SerializeToString()`. This avoids generating your own `*_pb2.py` and guarantees field compatibility with your installed `aioesphomeapi` version.

### Don’t implement Noise encryption initially

Plaintext is simplest:
- Use preamble `0x00`
- No cryptographic handshake

Noise encryption frames (preamble `0x01`) exist (`make_noise_packets` in `/.vendor/aioesphomeapi/aioesphomeapi/_frame_helper/packets.py`), but a working Noise implementation also requires duplicating `APINoiseFrameHelper`’s full handshake and cipher state; that’s intentionally out of scope for a “first mock”.

### AuthenticationRequest handling

In ESPro today, scanning constructs the client with `password=""` (empty string), which is **not** `None`, so the client will send an `AuthenticationRequest(password="")` when `login=True`.

Simplest approach: accept it and do nothing (don’t send `AuthenticationResponse`).

## Minimal “mock switch” checklist

Server must:
- Accept TCP connections on `6053`
- Parse plaintext frames (`0x00 + varuint(len) + varuint(type) + payload`)
- Respond to:
  - `HelloRequest` → `HelloResponse(api_version=1.14, name=..., server_info=...)`
  - `PingRequest` → `PingResponse`
  - `DeviceInfoRequest` → `DeviceInfoResponse` with fields used by ESPro
  - `ListEntitiesRequest` → `ListEntitiesSwitchResponse` + `ListEntitiesDoneResponse`
  - `SubscribeStatesRequest` → start sending `SwitchStateResponse`
  - `SwitchCommandRequest` → update state + emit `SwitchStateResponse`
  - `DisconnectRequest` → `DisconnectResponse` + close

