# Zigbee2MQTT MQTT protocol (reference for ESPro)

This document is an ESPro-oriented summary of the MQTT topic layout and request/response patterns used by **Zigbee2MQTT**.
It’s intended as a **reference model** for designing an ESPro MQTT surface that can coexist with mature `X2mqtt` projects with minimal conversion.

**Primary sources (upstream Zigbee2MQTT docs):**
- `temp/zigbee2mqtt.io/docs/guide/usage/mqtt_topics_and_messages.md`
- `temp/zigbee2mqtt.io/docs/guide/configuration/mqtt.md`
- `temp/zigbee2mqtt.io/docs/guide/configuration/device-availability.md`
- `temp/zigbee2mqtt.io/docs/guide/usage/groups.md`
- `temp/zigbee2mqtt.io/docs/guide/usage/exposes.md`

(Upstream website: https://www.zigbee2mqtt.io/)

---

## 1) Naming, base topic, and payload conventions

### Base topic
Zigbee2MQTT prefixes *all* topics with a configurable `base_topic` (default: `zigbee2mqtt`).
This is set in `configuration.yaml` under `mqtt.base_topic`.

### Device/group identifier (`FRIENDLY_NAME`)
Most per-device topics follow:

- `<base_topic>/<FRIENDLY_NAME>`

Where `FRIENDLY_NAME` is typically the Zigbee IEEE address (e.g. `0x00158d...`) unless a user-defined `friendly_name` exists.
Zigbee2MQTT allows `/` inside `friendly_name` to create “folders” in MQTT explorers (e.g. `kitchen/floor_light`).

### JSON-first
Device state and commands are **JSON objects** by default.

---

## 2) Device state publishing (telemetry)

### Topic
- `<base_topic>/<FRIENDLY_NAME>`

### Payload
A JSON object representing current state/measurements; keys depend on the device.
Examples (illustrative):

```json
{"temperature": 27.34, "humidity": 44.72}
```

### Caching behavior
Zigbee2MQTT can cache state and publish “full” payloads (not just deltas) depending on `advanced.cache_state*` settings.

### Alternative output modes
Zigbee2MQTT supports different MQTT output shapes (`advanced.output`):
- `json` (default): only JSON to `<base>/<friendly>`
- `attribute`: per-attribute topics (e.g. `<base>/<friendly>/state` with payload `ON`)
- `attribute_and_json`: both

**Takeaway for ESPro:** if you want maximum compatibility with existing tooling, keep JSON as the canonical format, but consider an optional “attribute topics” mode.

---

## 3) Controlling devices/groups (`/set`)

### Topic
- `<base_topic>/<FRIENDLY_NAME>/set`

### Payload
JSON object with desired fields, e.g.

```json
{"state":"ON", "brightness": 255}
```

If `FRIENDLY_NAME` refers to a **group**, the command applies to all members.

### Non-JSON convenience form
Zigbee2MQTT also supports publishing to an attribute sub-topic:
- `<base_topic>/<FRIENDLY_NAME>/set/<attribute>` with a plain payload

Example equivalence:
- topic: `<base>/lamp/set/state` payload: `ON`
- topic: `<base>/lamp/set` payload: `{"state":"ON"}`

**Takeaway for ESPro:** supporting both forms can make quick demos easier (MQTT Explorer/manual publishing), but JSON-only is simpler.

---

## 4) Reading device state (`/get`)

### Topic
- `<base_topic>/<FRIENDLY_NAME>/get`

### Payload
A JSON object where keys indicate which fields to retrieve (values often empty strings), e.g.

```json
{"state": ""}
```

Whether a property can be gotten/set is described by the device capability model (see Exposes below).

---

## 5) Availability (`/availability`)

### Topic
- `<base_topic>/<FRIENDLY_NAME>/availability`

### Payload (retained)

```json
{"state":"online"}
```

or

```json
{"state":"offline"}
```

Availability is configurable and distinguishes:
- **active** (mains-powered) devices that can be pinged
- **passive** (battery) devices that are judged by last check-in

Groups also receive availability (available if at least one member is available).

**Takeaway for ESPro:** publish availability as a retained topic; it’s foundational for dashboards.

---

## 6) “Bridge” topics (gateway/control-plane status)

Zigbee2MQTT exposes gateway-level topics under:
- `<base_topic>/bridge/...`

Common ones:

### `<base_topic>/bridge/state` (retained)
- `{"state":"online"}` on startup
- `{"state":"offline"}` right before stop

### `<base_topic>/bridge/info`
A JSON document with version/coordinator/network/config metadata (note: config excludes the network key).

### `<base_topic>/bridge/devices` (retained)
An inventory list of devices (IEEE, friendly name, endpoints, supported status, etc.).
This is the primary “device registry export”.

### `<base_topic>/bridge/groups` (retained)
Inventory of groups and members.

### `<base_topic>/bridge/event`
Events like device joined/left/interview status changes.

### `<base_topic>/bridge/logging`
Structured log messages published as JSON.

**Takeaway for ESPro:** mirroring the *shape* of this “bridge namespace” is the lowest-friction way to integrate multiple `X2mqtt` backends into one dashboard.

---

## 7) Request/response management API (`bridge/request` → `bridge/response`)

Zigbee2MQTT implements a management API via MQTT topics:

- Request:  `<base_topic>/bridge/request/<operation>`
- Response: `<base_topic>/bridge/response/<operation>`

### Response envelope
Responses are JSON and include:
- `status`: `"ok"` or `"error"`
- `data`: operation result payload
- `error`: error description (only when `status == "error"`)

### Transaction correlation
Requests may include a `transaction` field; if present, Zigbee2MQTT echoes it back in the response.
This makes it easy to correlate responses when multiple clients publish requests.

### Endpoint selection for device-involved operations
For certain device operations, Zigbee2MQTT supports selecting an endpoint by encoding it in identifiers (e.g. `device/left`) or via topic suffixing with an endpoint.

### Example (permit join)
Request:
- topic: `<base>/bridge/request/permit_join`
- payload: `{"time": 60, "transaction": 23}`

Response:
- topic: `<base>/bridge/response/permit_join`
- payload: `{"status":"ok", "data":{"time":60}, "transaction":23}`

**Takeaway for ESPro:** implement the same request/response envelope and `transaction` echo; it’s a proven pattern and keeps dashboards simple.

---

## 8) Capability model (“Exposes”)

Zigbee2MQTT publishes device capabilities in the retained device inventory (`<base>/bridge/devices`) via a per-device `definition.exposes` array.
The Exposes format includes:
- `type` (e.g. `binary`, `numeric`, `enum`, or composites like `light`)
- `name`, `label`, and `property`
- `access` bitmask describing state/set/get support

Access bitmask (3 bits):
- bit 1: appears in published state
- bit 2: writable via `/set`
- bit 3: readable via `/get`

**Takeaway for ESPro:** publish *some* machine-readable capability schema so UIs can generate forms/controls without hardcoding per-device behavior.

---

## 9) A minimal “compatibility subset” worth copying in ESPro

If ESPro wants to be “dashboard-friendly” in a world with Zigbee2MQTT, the following subset provides most value:

1. **Configurable base topic** (like `mqtt.base_topic`).
2. **Per-logical-device topics**:
   - `<base>/<logical_id>` state (JSON)
   - `<base>/<logical_id>/set` commands (JSON)
   - optional `<base>/<logical_id>/get`
   - `<base>/<logical_id>/availability` (retained)
3. **Bridge topics**:
   - `<base>/bridge/state` (retained online/offline)
   - `<base>/bridge/devices` (retained inventory)
   - `<base>/bridge/event` (join/leave/update lifecycle events)
4. **Management API**:
   - `<base>/bridge/request/<op>` → `<base>/bridge/response/<op>`
   - response envelope `{status,data,error?}` + `transaction` echo

This approach lets an aggregator/dashboard treat “ESPro” and “Zigbee2MQTT” as peers without modifying Zigbee2MQTT and without forcing both to share identical per-device payload schemas.
