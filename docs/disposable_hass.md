# Home Assistant as Disposable Frontend

A reference for using Home Assistant purely as a **rebuildable UI client** for an external control plane.

## Core Principle

> Home Assistant is a **stateless UI cache**.
> MQTT + external control plane are the **only source of truth**.

HA can be wiped entirely and rebuilt **without user-visible change** if and only if HA holds **zero authoritative state**. This is achievable with strict architectural constraints.

---

## The Registry Problem

Home Assistant maintains registries in `.storage/` that create state dependencies:

| Registry | Contents | Rebuildable? |
|----------|----------|--------------|
| `core.entity_registry` | entity_id ↔ unique_id mapping, customizations | Yes, via MQTT discovery |
| `core.device_registry` | Device metadata, area assignments | Yes, via MQTT discovery |
| `core.area_registry` | User-defined rooms/zones | Partial, via `suggested_area` |
| `core.restore_state` | Last known entity states | Yes, pure cache |
| `core.config_entries` | Integration configurations | Bypass with YAML config |

When `.storage/` is deleted and MQTT discovery messages replay, HA recreates entities. Without explicit control, entity_ids may get `_2`, `_3` suffixes on collision. The solution: **MQTT discovery's `default_entity_id` field** specifies exact entity_ids on creation.

---

## Non-Negotiable Constraints

### 1. MQTT-Only Integration

- No native HA device integrations (Zigbee, Z-Wave, BLE, USB)
- External control plane owns: device pairing, identity, state, availability
- All entities enter HA exclusively through MQTT discovery

### 2. Discovery Requirements

Every MQTT discovery payload **must** include:

| Field | Purpose |
|-------|---------|
| `unique_id` | Stable identifier managed by control plane; prevents duplicates |
| `default_entity_id` | Exact entity_id to use (include domain prefix) |
| `device.identifiers` | Stable device grouping |
| `suggested_area` | Auto-assigns room on first creation |

All discovery messages **must** use the MQTT retain flag.

### 3. Identity Rules

- `unique_id` = canonical identity (MAC, serial, or logical ID from control plane)
- `entity_id` = reproducible via `default_entity_id`
- **Never** rename entities in HA UI
- **Never** reference HA-generated `device_id` anywhere

### 4. YAML-Only Configuration

- Dashboards: `lovelace: mode: yaml`
- Automations: Labeled YAML blocks with `initial_state: true`
- **Never** use UI-created dashboards, automations, or helpers

---

## Configuration Reference

### configuration.yaml

```yaml
homeassistant:
  name: Home
  unit_system: metric
  time_zone: UTC

# Core web interface
frontend:
http:
api:
websocket_api:

# MQTT as sole entity source
mqtt:
  broker: mosquitto.local
  port: 1883
  username: ha
  password: !secret mqtt_password
  discovery: true
  discovery_prefix: homeassistant

# YAML-only dashboards
lovelace:
  mode: yaml
  dashboards:
    main:
      mode: yaml
      filename: dashboards/main.yaml

# YAML automations with labeled blocks
automation main: !include automations/main.yaml
script: !include scripts.yaml
scene: !include scenes.yaml

# EXPLICITLY EXCLUDED (do not add):
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

### Dashboard Example

```yaml
# dashboards/main.yaml
views:
  - title: Overview
    cards:
      - type: entities
        entities:
          - entity: sensor.living_room_temperature
          - entity: light.kitchen_main
          - entity: binary_sensor.front_door
```

Reference **entities only**. Never reference devices.

### Automation Example

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

Use **entity-based triggers only**. Never use device triggers.

---

## MQTT Discovery Specification

### Payload Structure

```json
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

**Topic:** `homeassistant/sensor/ctrl_bedroom_temp/config`
**Retain:** `true`

### What Discovery Controls

| Attribute | Controllable | Notes |
|-----------|--------------|-------|
| Initial `entity_id` | Yes | Via `default_entity_id` |
| Device grouping | Yes | Via `device.identifiers` |
| Suggested area | Yes | Applied on first creation only |
| Enabled by default | Yes | Via `enabled_by_default` |
| UI customizations | No | Friendly names, icons changed in UI are lost |
| Manual area changes | No | Only `suggested_area` survives rebuild |

### Removing Entities

Publish empty retained message to clear:

```bash
mosquitto_pub -t "homeassistant/sensor/old_device/config" -n -r
```

---

## Rebuild Workflow

### Startup Sequence

1. **MQTT broker starts** (must be running before HA)
2. **Control plane publishes** retained discovery messages to `homeassistant/+/+/config`
3. **HA container starts**
4. HA connects to broker, subscribes to `homeassistant/#`
5. Broker replays retained discovery messages
6. HA creates entities using `default_entity_id` from payloads
7. HA publishes birth message: `homeassistant/status` = `online`
8. **Wait 10-15 seconds** (documented race condition)
9. Control plane publishes state updates

### Docker Compose

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
      - ./ha-config:/config  # YAML files only
    network_mode: host
    depends_on:
      - mosquitto
    restart: unless-stopped
```

### Persistent vs Ephemeral

**Persistent (version-controlled):**
- `configuration.yaml`
- `secrets.yaml`
- `dashboards/*.yaml`
- `automations/*.yaml`

**Ephemeral (safe to wipe):**
- `.storage/` (entire directory)
- `home-assistant_v2.db`

---

## Failure Modes & Mitigations

| Failure | Cause | Mitigation |
|---------|-------|------------|
| Ghost entities | Retained discovery not cleared on removal | Publish empty retained config on device removal |
| Entity ID drift | Renamed discovery payload or collision | Pin `default_entity_id`; ensure uniqueness |
| Broken automations | Device-based triggers | Use entity-based YAML triggers only |
| UI differences | UI edits stored in `.storage` | YAML-only dashboards and automations |
| Re-login required | Auth wiped with `.storage` | Accept, or persist `.storage/auth*` files |
| Duplicate entities | Missing or duplicate `unique_id` | Control plane ensures globally unique IDs |
| State unavailable | States published before HA ready | Wait 10-15s after birth message before publishing |
| MQTT not configured | Config entries wiped | Use YAML MQTT config, not UI setup |

---

## Reference Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    EXTERNAL CONTROL PLANE                   │
│         (Device registry, entity definitions, state)        │
│         Examples: espro, Zigbee2MQTT, Node-RED, custom      │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      │ MQTT Discovery + State
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                      MQTT BROKER                            │
│  - Retained discovery: homeassistant/+/+/config             │
│  - State topics: ctrl/+/+/state                             │
│  - Birth/LWT: homeassistant/status                          │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│               HOME ASSISTANT (DISPOSABLE)                   │
│                                                             │
│  Persistent:              │  Ephemeral:                     │
│  ├── configuration.yaml   │  └── .storage/* (rebuilt from   │
│  ├── dashboards/*.yaml    │       MQTT discovery)           │
│  ├── automations/*.yaml   │                                 │
│  └── secrets.yaml         │                                 │
└─────────────────────────────────────────────────────────────┘
```

---

## Validation Checklist

### Pre-Deployment

- [ ] All discovery payloads include `unique_id` and `default_entity_id`
- [ ] All discovery messages use retain flag
- [ ] `configuration.yaml` excludes `default_config` and all discovery integrations
- [ ] Dashboards use `lovelace: mode: yaml`
- [ ] Automations use labeled YAML blocks with `initial_state: true`
- [ ] Automations use entity-based triggers only (no device triggers)
- [ ] MQTT credentials in `secrets.yaml` (not UI-configured)
- [ ] Control plane handles 10-15s delay after HA birth message

### Litmus Test

Delete HA completely (config + `.storage` + DB) and restart. If any of the following occur, the architecture is **invalid**:

- [ ] Any device must be re-paired
- [ ] Any entity_id changes
- [ ] Any automation breaks
- [ ] Any dashboard card is missing

### Feasibility Summary

| Requirement | Status |
|-------------|--------|
| Dashboards restored identically | ✅ Feasible (YAML mode) |
| Entity IDs stable across rebuild | ✅ Feasible (`default_entity_id`) |
| No duplicate entities | ✅ Feasible (`unique_id`) |
| Automations work after rebuild | ✅ Feasible (YAML + `initial_state`) |
| Device associations preserved | ✅ Feasible (MQTT discovery) |
| User UI customizations preserved | ⚠️ Partial (discovery-controlled only) |
| Area assignments preserved | ⚠️ Partial (`suggested_area` on first creation) |
| History/statistics preserved | ❌ Not feasible (use external DB or accept loss) |

---

## Conclusion

Home Assistant functions as a disposable frontend when treated as a **stateless UI cache**. The critical enablers:

1. **MQTT discovery** with `default_entity_id` for stable entity identity
2. **YAML-only** dashboards and automations
3. **No native integrations**—external control plane owns all devices

The `.storage/` directory becomes rebuildable cache rather than authoritative state. User customizations made in HA's UI will not survive rebuild—all configuration must flow from the external control plane through MQTT discovery payloads.
