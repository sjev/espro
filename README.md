# ESPro

*A control plane for ESPHome fleets: manage devices behind stable logical identities.*

> **Status:** Early prototype. Core registry and scanning work. Feedback welcome.

## The Problem

ESPHome ties device identity to physical hardware. When a device fails and gets replaced:

- Home Assistant entity IDs change
- Dashboards break
- Automations need manual updates
- 30+ minutes of recovery work per device

This is [one of the most common ESPHome + Home Assistant frustrations](docs/esphome_pain_points.md)—documented across forums, GitHub issues, and Reddit.

## The Solution

**Decouple logical identity from physical hardware.**

ESPro maintains a device registry mapping logical names to physical devices. When hardware fails, update the mapping—everything else stays stable.

```toml
# ~/.local/share/espro/devices.toml
[logical_devices]
outdoor_light_1 = { physical = "esp-sonoff-1.local" }
chicken_scale = { physical = "esp32-coop.local" }
```

Device dies? Swap in new hardware, update the mapping, done.

## Architecture

```
┌─────────────────────────────────┐
│  Home Assistant / MQTT clients  │  ← stable entity IDs
└───────────────┬─────────────────┘
                │
┌───────────────▼─────────────────┐
│      ESPro (control plane)      │  ← logical ↔ physical registry
└───────────────┬─────────────────┘
                │
┌───────────────▼─────────────────┐
│   Physical ESPHome devices      │  ← swappable hardware
└─────────────────────────────────┘
```

Three layers, clear responsibilities:
- **ESPHome** — Firmware and I/O on physical hardware
- **ESPro** — Device registry and lifecycle management
- **Home Assistant** — Automations, dashboards, UI

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
# 1. Initialize configuration
uv run espro config init

# 2. Discover ESPHome devices via mDNS
uv run espro scan

# 3. Register a logical device
uv run espro add kitchen_sensor esp-kitchen.local

# 4. List registered devices
uv run espro list

# 5. Validate mappings against last scan
uv run espro validate
```

For testing without real hardware:
```bash
# Terminal 1: Start mock device
uv run espro mock --name test-device

# Terminal 2: Discover and register it
uv run espro scan
uv run espro add my_sensor test-device.local
```

## Roadmap

**Phase 1: Registry (current)**
- Device discovery and scanning
- Logical ↔ physical mapping in TOML
- Validation and drift detection

TODO:

- switch from ip to mac-based mapping.

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
# Setup
uv sync --group dev

# Run CLI
uv run espro --help

# Run tests
uv run pytest

# Lint & format
uv run invoke lint
uv run invoke format
```

**Config locations:**
- Config: `~/.config/espro/config.toml` (override with `ESPRO_CONFIG`)
- Data: `~/.local/share/espro/`

See [CLAUDE.md](CLAUDE.md) for architecture details and development notes.

## License

MIT
