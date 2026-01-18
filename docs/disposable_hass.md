# Home Assistant as disposable frontend: conditionally feasible - claude

Using Home Assistant purely as a **rebuildable UI client** is **partially feasible**, but requires strict architectural constraints. The core challenge: HA's internal registries store the mapping between external identifiers and user-visible entity_ids. Without careful design, a fresh HA instance creates different entity_ids, breaking dashboards and automations.

**The solution exists** through MQTT discovery's `default_entity_id` field combined with YAML-only configuration. When HA's `.storage` is deleted and discovery messages are replayed, entities can be recreated with **identical entity_ids**—if the external control plane specifies them explicitly. However, certain user customizations (areas, friendly names changed in UI, icons) will not survive rebuild unless the external system also controls these via discovery payloads.

---

## The registry problem and why it matters

Home Assistant maintains three critical registries in `.storage/` that create state dependencies:

| Registry | Contents | Deletable? |
|----------|----------|------------|
| `core.entity_registry` | entity_id ↔ unique_id mapping, user customizations, disabled/hidden states | **No** — causes entity_id instability |
| `core.device_registry` | Device metadata, user-assigned names, area assignments | **Partial** — hardware info regenerates, customizations lost |
| `core.area_registry` | User-defined rooms/zones | **No** — 100% user-created data |
| `core.restore_state` | Last known entity states (15-min cache) | **Yes** — pure cache, regenerates automatically |

When `core.entity_registry` is deleted and MQTT discovery messages replay, HA recreates entities as if new. Without explicit control, entity_ids are generated from device names and entity names—which may produce `_2`, `_3` suffixes if naming collisions occur. The critical insight: **MQTT discovery's `default_entity_id` field bypasses this problem** by explicitly specifying the exact entity_id on first creation.

---

## MQTT discovery controls entity identity—with caveats

The `default_entity_id` field (which replaces the deprecated `object_id` field removed in HA 2026.4) provides explicit control over entity_id generation:

```json
{
  "name": "Living Room Temperature",
  "default_entity_id": "sensor.living_room_temperature",
  "unique_id": "ctrl_plane_sensor_001",
  "state_topic": "home/living_room/temperature",
  "device": {
    "identifiers": ["living_room_hub"],
    "name": "Living Room Hub",
    "suggested_area": "Living Room"
  }
}
```

**What external discovery CAN control:**
- Initial `entity_id` via `default_entity_id` (works on fresh registry)
- Device name, manufacturer, model via `device` block
- Suggested area via `suggested_area` (HA may use this on first creation)
- Whether entity is enabled by default (`enabled_by_default: false`)

**What external discovery CANNOT override:**
- Entity Registry customizations (if a user renamed entity_id in HA UI, registry wins)
- Area assignments made manually in HA
- Icons or friendly names changed via HA UI

The `unique_id` field is **essential**—entities without it are not restored at startup and cannot be customized via HA's UI. The topic path's `<object_id>` portion (e.g., `homeassistant/sensor/my_object_id/config`) does **not** affect entity_id; it only organizes MQTT topics.

---

## Required configuration for disposable operation

### Disable all hardware discovery

Remove `default_config:` and explicitly exclude discovery integrations:

```yaml
# configuration.yaml — discovery disabled
homeassistant:
  name: Home
  unit_system: metric
  time_zone: UTC

# Core web interface
frontend:
http:
api:
websocket_api:
config:

# MQTT as sole entity source
mqtt:
  broker: mosquitto.local
  discovery: true
  discovery_prefix: homeassistant

# YAML-only dashboards
lovelace:
  mode: yaml
  dashboards:
    main:
      mode: yaml
      filename: dashboards/main.yaml

# YAML automations (labeled blocks, not UI-managed)
automation main: !include automations/main.yaml
script: !include scripts.yaml
scene: !include scenes.yaml

# Explicitly NOT included:
# default_config:
# dhcp:
# ssdp:
# zeroconf:
# usb:
# bluetooth:
# recorder:
# history:
# logbook:
```

This configuration ensures HA only receives entities from MQTT discovery—no network scanning, no USB device detection, no mDNS discovery.

### YAML dashboards reference logical entity_ids

Dashboards in YAML mode are fully external—no `.storage/lovelace*` dependency:

```yaml
# dashboards/main.yaml
views:
  - title: Overview
    cards:
      - type: entities
        entities:
          - entity: sensor.living_room_temperature  # Logical ID from discovery
          - entity: light.kitchen_main
          - entity: binary_sensor.front_door
```

When using `lovelace: mode: yaml`, the dashboard is defined entirely by your YAML file. Deleting `.storage/lovelace*` has no effect on YAML-mode dashboards.

### Automations use labeled YAML blocks

UI-created automations store state in `.storage/`. YAML-defined automations with labeled blocks avoid this dependency:

```yaml
# automations/main.yaml
- alias: "Kitchen light auto-off"
  id: kitchen_auto_off
  initial_state: true  # Force enabled on startup
  triggers:
    - trigger: state
      entity_id: light.kitchen_main
      to: "on"
      for: "01:00:00"
  actions:
    - action: light.turn_off
      target:
        entity_id: light.kitchen_main
```

The `initial_state: true` ensures automations are enabled on fresh startup rather than restoring from (nonexistent) previous state.

---

## Rebuild workflow with external MQTT broker

### Startup sequence

**Order matters:** MQTT broker must be running before HA starts.

1. **Start MQTT broker** (Mosquitto)
2. **External control plane publishes retained discovery messages** to `homeassistant/+/+/config` topics
3. **Start Home Assistant container**
4. HA connects to broker, subscribes to `homeassistant/#`
5. Broker replays all retained discovery messages
6. HA creates entities using `default_entity_id` from payloads
7. HA publishes birth message to `homeassistant/status` with payload `online`

**Critical timing issue:** A documented race condition (GitHub #39007) means HA may take **10-15 seconds after the birth message** to actually be ready to receive state updates. External systems should add a delay after seeing `online` before publishing state updates.

### MQTT discovery payload structure for full control

```json
// Topic: homeassistant/sensor/ctrl_bedroom_temp/config
// Retain: true
{
  "name": "Bedroom Temperature",
  "default_entity_id": "sensor.bedroom_temperature",
  "unique_id": "ctrl_plane_bedroom_temp_001",
  "device_class": "temperature",
  "unit_of_measurement": "°C",
  "state_topic": "ctrl/bedroom/temperature/state",
  "availability_topic": "ctrl/bedroom/temperature/available",
  "device": {
    "identifiers": ["ctrl_bedroom_hub"],
    "name": "Bedroom Environmental Hub",
    "manufacturer": "Control Plane",
    "model": "Virtual Device",
    "suggested_area": "Bedroom"
  },
  "origin": {
    "name": "external_control_plane",
    "sw_version": "1.0"
  }
}
```

**Key fields for disposability:**
- `default_entity_id`: Exact entity_id to use (include domain prefix)
- `unique_id`: Stable identifier the control plane manages; must be globally unique
- `suggested_area`: HA will assign this area on first entity creation
- Retain flag: **Must be set** so messages replay on fresh HA start

### Docker deployment

```yaml
services:
  mosquitto:
    image: eclipse-mosquitto:2
    volumes:
      - ./mosquitto/config:/mosquitto/config
      - ./mosquitto/data:/mosquitto/data
    ports:
      - "1883:1883"
    restart: unless-stopped

  homeassistant:
    image: ghcr.io/home-assistant/home-assistant:stable
    volumes:
      - ./ha-config:/config  # Contains only YAML files
    network_mode: host
    depends_on:
      - mosquitto
    restart: unless-stopped
```

For truly disposable operation, the `/config` volume contains only:
- `configuration.yaml` and included YAML files
- `secrets.yaml` for MQTT credentials
- Dashboard YAML files

The `.storage/` directory can be ephemeral if you accept the constraints below.

---

## Known failure modes and edge cases

### Entity_id collision on rebuild

If two discovery messages produce the same `default_entity_id`, the second entity gets a `_2` suffix. **Prevention:** External control plane must ensure unique `default_entity_id` values across all discovery payloads.

### Ghost entities from stale retained messages

If a device is removed but its retained discovery message persists on the broker, HA recreates the entity on every restart. **Solution:** Control plane must publish empty payload to the config topic to clear retained messages:

```bash
mosquitto_pub -t "homeassistant/sensor/old_device/config" -n -r
```

### Area assignments don't survive rebuild

The `suggested_area` field only applies when an entity is first created. If HA's area registry is deleted, areas must be recreated and `suggested_area` in discovery will re-apply them. However, **manual area assignments made in HA UI are lost**.

### Authentication tokens invalidated

Fresh `.storage/` means new authentication. Long-lived access tokens used by external services (Node-RED, mobile apps) become invalid. **Mitigation:** Use service accounts with tokens regenerated as part of rebuild process, or persist `.storage/auth*` files.

### MQTT integration config entry

The MQTT broker connection settings are stored in `.storage/core.config_entries`. On fresh container, MQTT integration must be reconfigured. **Workaround:** Use deprecated YAML configuration for MQTT (still functional):

```yaml
mqtt:
  broker: mosquitto.local
  port: 1883
  username: ha
  password: !secret mqtt_password
  discovery: true
```

---

## Feasibility assessment

| Requirement | Status | Notes |
|-------------|--------|-------|
| Dashboards restored identically | ✅ **Feasible** | YAML mode dashboards fully external |
| Entity_ids stable across rebuild | ✅ **Feasible** | Requires `default_entity_id` in all discovery payloads |
| No duplicate entities | ✅ **Feasible** | `unique_id` prevents duplicates; control plane manages uniqueness |
| No device reconfiguration | ✅ **Feasible** | MQTT discovery recreates device associations |
| Automations work after rebuild | ✅ **Feasible** | YAML automations with `initial_state: true` |
| User customizations preserved | ⚠️ **Partial** | Only if controlled via discovery; UI changes lost |
| Area assignments preserved | ⚠️ **Partial** | `suggested_area` works on fresh creation only |
| History/statistics preserved | ❌ **Not feasible** | Recorder database is local; use external DB or accept loss |

**Overall: PARTIALLY FEASIBLE** with strict constraints.

---

## Reference architecture for disposable HA

```
┌─────────────────────────────────────────────────────────────┐
│                    EXTERNAL CONTROL PLANE                    │
│  (Maintains device registry, entity definitions, state)      │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      │ MQTT Discovery + State
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                     MOSQUITTO BROKER                         │
│  - Retained discovery messages (homeassistant/+/+/config)    │
│  - State topics (ctrl/+/+/state)                             │
│  - Birth/LWT (homeassistant/status)                          │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                  HOME ASSISTANT (DISPOSABLE)                 │
│                                                              │
│  Persistent (version-controlled):                            │
│  ├── configuration.yaml (MQTT config, discovery disabled)    │
│  ├── dashboards/*.yaml (YAML-mode Lovelace)                  │
│  ├── automations/*.yaml (labeled YAML blocks)                │
│  └── secrets.yaml                                            │
│                                                              │
│  Ephemeral (.storage/):                                      │
│  ├── core.entity_registry (rebuilt from discovery)           │
│  ├── core.device_registry (rebuilt from discovery)           │
│  └── core.config_entries (MQTT configured in YAML)           │
└─────────────────────────────────────────────────────────────┘
```

### Minimum viable configuration checklist

1. **MQTT discovery payloads include:** `unique_id`, `default_entity_id`, `device.identifiers`, `suggested_area`
2. **All discovery messages use retain flag**
3. **HA configuration excludes:** `default_config`, all discovery integrations, `recorder`
4. **Dashboards use:** `lovelace: mode: yaml`
5. **Automations use:** Labeled YAML blocks with `initial_state: true`
6. **External system handles:** 10-15 second delay after HA birth message before state updates
7. **MQTT broker credentials in:** `secrets.yaml` (not UI-configured)

---

## Conclusion

Home Assistant can function as a disposable frontend for an external control plane, but only under constrained conditions. The critical enabler is MQTT discovery's `default_entity_id` field, which allows the external system to dictate exact entity_ids that remain stable across HA rebuilds. Combined with YAML-only dashboards and automations, this creates a reproducible UI layer.

**What works well:** Entity creation, device grouping, basic automations, dashboards—all can be externally controlled and rebuilt identically.

**What requires compromise:** User customizations made in HA's UI (friendly names, icons, manual area assignments) will not survive rebuild unless the external control plane handles them via discovery payloads. History and statistics require an external database or must be accepted as ephemeral.

For production deployment, the recommended approach is to treat `.storage/` as **rebuildable cache** rather than truly ephemeral—allowing HA to maintain its registries during normal operation while having the capability to fully reconstruct from external MQTT discovery when needed.


# Disposable HASS - ChatGPT


## Executive verdict

**Feasible**, with hard constraints.
HA can be wiped entirely and rebuilt **without user-visible change** *if and only if* HA holds **zero authoritative state**.

---

## Core principle

> Home Assistant is a **stateless UI cache**.
> MQTT + external control plane are the **only source of truth**.

---

## Required architectural constraints (non-negotiable)

### 1. Integration model

* **MQTT only**
* No native HA device integrations
* No Zigbee/Z-Wave/BLE/USB passed into HA
* External control plane owns:

  * device pairing
  * identity
  * state
  * availability
  * automation logic (optionally)

### 2. Discovery model

* **MQTT Discovery required**
* Every entity **must** provide:

  * `unique_id` (stable, external, never regenerated)
  * stable name or explicit `default_entity_id`
* Discovery configs **must be retained**
  (`homeassistant/.../config` topics with `retain=true`)

OR

* External system republishes discovery on HA birth:

  * listen to `homeassistant/status == online`

### 3. Identity rules

* `unique_id` = canonical identity (MAC / serial / logical ID)
* `entity_id` must be reproducible:

  * either via `default_entity_id`
  * or via stable naming rules
* Never rename entities in HA UI
* Never rely on HA-generated IDs

### 4. Device model

* Use MQTT `device:` block with stable `identifiers`
* Use `suggested_area` for auto-room assignment
* **Never reference HA `device_id` anywhere**

---

## What HA state is allowed to be ephemeral

Safe to wipe every time:

* `.storage/`
* entity registry
* device registry
* history DB
* UI state
* dashboards (if YAML)
* automations (if YAML)

Must be provided at startup:

* `configuration.yaml`
* MQTT connection config
* Lovelace YAML
* automation YAML

---

## What NOT to use in HA

* UI-created dashboards
* UI-created automations
* Device-based triggers/conditions
* Helpers with restored state (`input_*`)
* Any feature that persists logic/state in `.storage`
* Default `default_config` (disable discovery)

---

## YAML rules

### configuration.yaml

* No `default_config`
* Explicitly enable only:

  * `mqtt`
  * `automation`
  * `frontend`
  * `lovelace: mode: yaml`

### Dashboards

* YAML-only (`ui-lovelace.yaml`)
* Reference **entities only**
* Never reference devices

### Automations

* YAML-only
* Entity-based triggers only
* No device triggers
* No UI toggles expected to persist

---

## Rebuild workflow (target behavior)

1. HA container deleted (config + `.storage` + DB gone)
2. New HA container starts
3. Connects to MQTT broker
4. Broker feeds retained discovery configs
5. Entities + devices recreated identically
6. Dashboards load from YAML
7. Automations activate
8. User sees **no change**

Expected transient:

* brief `unavailable` until first state publish

---

## Known failure modes (and mitigations)

### Ghost entities

**Cause:** retained discovery not cleared
**Fix:** external control plane must publish empty retained config on removal

### Entity ID drift

**Cause:** renamed discovery payload
**Fix:** pin `default_entity_id` or keep names immutable

### Broken automations after rebuild

**Cause:** device-based triggers
**Fix:** entity-based YAML only

### UI differences after rebuild

**Cause:** UI edits stored in `.storage`
**Fix:** YAML-only UI

### Re-login required

**Cause:** auth wiped
**Fix:** acceptable, or pre-seed auth files if needed

---

## Minimal reference architecture

```
[ Devices ]
     |
[ External control plane ]
  - Zigbee2MQTT / Node-RED / custom
  - Owns identity + logic
     |
[ MQTT broker ]
  - retained discovery
  - retained state (where relevant)
     |
[ Home Assistant (Docker) ]
  - mqtt only
  - YAML UI + YAML automations
  - no hardware access
```

---

## Litmus test (use this to validate designs)

If HA is deleted and:

* any device must be re-paired ❌
* any entity ID changes ❌
* any automation breaks ❌
* any dashboard card is missing ❌

→ architecture is **invalid**

