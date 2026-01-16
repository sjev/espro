# ESPro

*An infrastructure layer for ESPHome fleets that separates logical device identity from physical hardware.*

> **Status:** Early prototype. Core registry and scanning work. Feedback and co-developers welcome.

## Who this is for (and who it is not)

ESPro is for ESPHome / Home Assistant users who:
- Run more than a handful of devices
- Care about long-term maintainability and stability
- Think in terms of infrastructure as code (versioned config, reproducibility)

It is not for:
- Plug-and-play smart home users
- People who prefer GUIs over CLI tools



## The Problem

In ESPHome and Home Assistant, device identity is tied to hardware identifiers (for example, a MAC address or an mDNS name). When hardware fails and is replaced, Home Assistant discovers a *new* device and creates new entities. Automations, dashboards, and entity references usually need to be fixed by hand.

There is no native workflow to replace hardware while keeping the same logical role.

This affects both common ESPHome usage patterns:

**Per-device configuration ("pets")**
Each device has its own YAML file. Replacing hardware creates a new device with new entities. At scale, this leads to YAML duplication and manual repair work.

**Shared configuration ("cattle")**
A single YAML is reused with `name_add_mac_suffix: true`. This reduces duplication, but the final device name is only known after boot, and there is no built-in way to bind a specific device to a predefined role such as *kitchen light*.

In both cases, there is no abstraction between *what a device does* and *which piece of hardware currently does it*.

## Core Idea

**Two-layer identity model**

| Layer        | Example          | Stability                           |
| ------------ | ---------------- | ----------------------------------- |
| **Logical**  | `kitchen_switch` | Stable across hardware replacements |
| **Physical** | `switch-aabbcc`  | Tied to a specific ESP board        |

ESPro keeps the mapping between these layers.

When hardware fails:

1. Flash a replacement board with the same ESPHome firmware
2. Discover the new device on the network
3. Update one mapping: `kitchen_switch → switch-ddeeff`
4. Everything downstream keeps working

Home Assistant and automations only ever reference the logical name.

## Physical Identifier

The ESPHome mDNS name is used as the physical identifier because:

* With `name_add_mac_suffix`, it is hardware-bound
* It is human-readable and routable on the local network
* It is already used by `aioesphomeapi`
* No custom firmware changes are required

## Architecture

ESPro follows the same pattern as `zigbee2mqtt`: bridge a device protocol to MQTT using stable logical identities.

```
┌───────────────────────────────────────────────────────────────────┐
│                   MQTT Bus (logical identities)                   │
└───────┬─────────────────┬─────────────────┬─────────────────┬─────┘
        │                 │                 │                 │
    ┌───▼───┐       ┌─────▼─────┐     ┌─────▼─────┐     ┌─────▼─────┐
    │ ESPro │       │zigbee2mqtt│     │   Home    │     │   your    │
    │daemon │       │           │     │ Assistant │     │   tools   │
    └───┬───┘       └─────┬─────┘     └───────────┘     └───────────┘
        │                 │
    ESPHome            Zigbee
   Native API          devices
```

Home Assistant talks to ESPro (currently via MQTT, later via an integration). ESPHome devices are accessed via the native API behind ESPro. Entity IDs remain stable even when hardware is replaced.

> *The daemon is not yet implemented. Currently ESPro provides CLI tools for registry management.*

## Responsibilities

* **ESPHome** — Firmware and hardware interaction
* **ESPro** — Registry, identity mapping, MQTT bridge
* **Home Assistant** — Automations and UI (via MQTT)

## Philosophy

* **Plain text config** — Git-tracked TOML. No database.
* **Infrastructure as code** — Reproducible and offline-capable.
* **Unix mindset** — Do one thing well. Don't replace ESPHome or Home Assistant.
* **Boring tech** — TOML, JSON, asyncio.

## Demo

```bash
# Setup
uv sync
source .venv/bin/activate

# Initialize configuration
espro config init

# Discover ESPHome devices
espro scan

# Register a logical device
espro add kitchen_switch switch-aabbcc

# List registry
espro list

# Validate mappings
espro validate
```

Testing without hardware (useful for development and CI):

```bash
# Terminal 1
espro mock --name test-device

# Terminal 2
espro scan
espro add my_sensor test-device
```

## Roadmap

**Registry** ✓
- [x] mDNS discovery
- [x] Logical ↔ physical registry (TOML)
- [x] Mapping validation and drift detection
- [x] Mock devices for testing

**MQTT daemon** (next)
- [ ] Connect to physical devices via `aioesphomeapi`
- [ ] Publish state under logical topic names
- [ ] Forward MQTT commands to physical devices
- [ ] Reconnection handling
- [ ] Docker packaging

## Development

```bash
uv sync --group dev
source .venv/bin/activate

espro --help
pytest
invoke lint
invoke format
```

**Config paths**

* Config: `~/.config/espro/config.toml` (`ESPRO_CONFIG` override)
* Data: `~/.local/share/espro/`

Issues, ideas, and PRs welcome.


## Contributing

You can contribute by engaging in discussions on:

* system architecture
* scalability and reliability
* how to solve "updates & features vs LTS stability" for home automation
* how to open the open-source home automation ecosystem to professional installers

AND/OR

* co-development of a production-grade automation system based on open-source blocks.


## License

MIT
