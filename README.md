# ESPro

*A control plane for ESPHome fleets: manage devices behind stable logical identities.*

> **Status:** Early prototype. Core registry and scanning work. Feedback welcome.

## The Problem

In ESPHome and Home Assistant, device identity is tied to hardware identifiers (e.g. MAC address). When hardware is replaced, Home Assistant discovers a new device and creates new entities, which typically requires manual updates to automations, dashboards, and entity references. There is no native workflow to replace hardware while preserving a logical role.

This affects both common ESPHome patterns:

**Per-device configuration (“pets”)**
Each device has its own YAML file. Replacing hardware results in a new device and new entities, requiring manual reassignment. At scale, this leads to many nearly identical YAML files.

**Shared configuration (“cattle”)**
A single YAML is reused with `name_add_mac_suffix: true`, reducing duplication. However, the final device name is only known after boot, and there is no built-in way to associate a specific device with a predefined logical role (e.g. *kitchen light*).

In both cases, there is no abstraction between physical device identity and logical function, making hardware replacement and long-term maintenance unnecessarily manual.


## Core Idea

**Two-layer identity model:**

| Layer        | Example          | Stability                           | Defined by                    |
| ------------ | ---------------- | ----------------------------------- | ----------------------------- |
| **Logical**  | `kitchen_switch` | Stable across hardware replacements | User (ESPro registry)         |
| **Physical** | `switch-aabbcc`  | Tied to hardware                    | ESPHome mDNS name (MAC-based) |

ESPro maintains the mapping between these layers. When hardware fails:

1. Flash a replacement board with the same firmware
2. Discover the new device on the network (`switch-ddeeff`)
3. Update a single mapping: `kitchen_switch` → `switch-ddeeff`
4. Downstream systems continue to see the same logical device

## Physical Identifier Choice

The ESPHome mDNS name is used as the physical identifier because:

* With `name_add_mac_suffix`, it is hardware-bound
* It is human-readable and routable on the local network
* It is already used by `aioesphomeapi` for device communication
* No custom firmware changes are required

## Architecture

```
┌─────────────────────────────────┐
│  Home Assistant / MQTT clients  │  ← stable logical identities
└───────────────┬─────────────────┘
                │
┌───────────────▼─────────────────┐
│        ESPro (control plane)    │  ← logical ↔ physical mapping
└───────────────┬─────────────────┘
                │
┌───────────────▼─────────────────┐
│    Physical ESPHome devices     │  ← replaceable hardware
└─────────────────────────────────┘
```

## Responsibilities

* **ESPHome** — Firmware, I/O, and hardware interaction
* **ESPro** — Device registry, identity mapping, and lifecycle management
* **Home Assistant** — Automations, dashboards, and user interface

## What Works Today

| Feature | Status |
|---------|--------|
| mDNS discovery (zeroconf) | ✅ Working |
| Device registry (TOML-based) | ✅ Working |
| Logical ↔ physical mapping | ✅ Working |
| Mapping validation | ✅ Working |
| Mock device for testing | ✅ Working |
| MQTT bridge | 🔜 Planned |
| HA integration | 🔜 Planned |

## Demo Walkthrough

```bash
# Setup
uv sync
source .venv/bin/activate

# Initialize configuration
espro config init

# Discover ESPHome devices via mDNS
espro scan

# Register a logical device
espro add kitchen_switch switch-aabbcc

# List registered devices
espro list

# Validate mappings against last scan
espro validate
```

For testing without real hardware:
```bash
# Terminal 1: Start mock device
espro mock --name test-device

# Terminal 2: Discover and register it
espro scan
espro add my_sensor test-device
```

## Roadmap

**Phase 1: Registry (current)**
- Device discovery and scanning
- Logical ↔ physical mapping in TOML
- Validation and drift detection

**Phase 2: MQTT Bridge**
- Expose logical devices to MQTT
- Automatic re-routing on hardware changes
- Entity ID stability for Home Assistant

**Phase 3: Lifecycle Management**
- Device commissioning workflows
- Firmware deployment coordination
- Fleet-wide operations

## Philosophy

**Plain text wins** — Configuration in Git-tracked TOML. No database. Audit trail via `git log`, rollback via `git revert`, backup via `git push`.

**Infrastructure as code** — Reproducible deployments. Version-controlled configuration. Offline-capable.

**Unix philosophy** — Do one thing well. Don't replace ESPHome, MQTT, or Home Assistant—complement them.

**Boring technology** — TOML, JSON, asyncio. Nothing exotic.

---

## Development

```bash
uv sync --group dev
source .venv/bin/activate

espro --help
pytest
invoke lint
invoke format
```

**Config locations:**
- Config: `~/.config/espro/config.toml` (override with `ESPRO_CONFIG`)
- Data: `~/.local/share/espro/`

See [CLAUDE.md](CLAUDE.md) for architecture details and development notes.

## License

MIT
