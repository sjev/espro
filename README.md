# ESPro

*ESPro is a control plane for ESPHome fleets: register, program, and operate devices behind stable logical identities (with an optional MQTT bridge).*



## The Problem

ESPHome ties device identity to physical hardware. When a broken device gets replaced:

- All Home Assistant entity IDs change
- Dashboards break
- Automations need manual updates
- 30+ minutes of recovery work per device

This tool aims to simplify device commissioning and management for professional installers and power users who want to treat home infrastructure as code.

## The Solution

**A control plane for ESPHome devices.**

ESPro maintains a device registry (logical ↔ physical), supports lifecycle workflows (replacement, commissioning, programming), and can optionally expose devices into an MQTT domain.

Home Assistant connects to stable logical devices (`outdoor_light_1`), not physical hardware. When a device breaks, update a registry file and restart—entity IDs stay stable, automations keep working.
```toml
# ~/.local/share/espro/devices.toml
[logical_devices]
outdoor_light_1 = { physical = "esp-sonoff-1.local" }
chicken_scale = { physical = "esp32-coop.local" }
```

Device dies? Change the IP, reload ESPro mappings. Done.

## Architecture
```
Home Assistant (stable entity IDs)
(or other consumers via MQTT)
    ↓
ESPro (device registry + control plane)
    ↓
Physical ESPHome Devices (swappable)
```

Three layers with clear responsibilities:

- **ESPHome** - Firmware and I/O
- **ESPro** - Hardware abstraction and lifecycle management
- **Home Assistant** - Automations and UI

## Philosophy

**Boring technology**: Docker, TOML, Git, REST—nothing exotic.

**Plain text wins**: Configuration in Git-tracked TOML. No database, ever. Audit trail via `git log`, rollback via `git revert`, backup via `git push`.

**Infrastructure as code**: Reproducible deployments. Version-controlled configuration. Offline-capable.

**Unix philosophy**: Do one thing well—provide a device registry + lifecycle control plane. Don't replace ESPHome, MQTT, or Home Assistant.

## Status

**Early development.** Validating technical feasibility and gathering community feedback.

Target audience: Professional installers managing 10-1000+ devices across single or multiple sites who need reproducible deployments and version stability.

## Questions?

This is a proof-of-concept. Feedback is welcome.

---


## Development

**Quick start:**
1. Install [uv](https://docs.astral.sh/uv/getting-started/installation/)
2. Install dependencies: `uv sync --group dev`
3. Initialize config: `uv run espro config init`
4. Run CLI: `uv run espro --help`
5. Run tests: `uv run pytest`

**Available invoke tasks** (optional, install with `uv tool install invoke`):
- `invoke lint` - Run ruff and mypy
- `invoke test` - Run tests with coverage
- `invoke format` - Format code with ruff
- `invoke clean` - Remove untracked files (interactive)

**Mock device for testing:**
```bash
# Terminal 1: Start a mock ESPHome device
uv run espro mock --name test-device --port 6053

# Terminal 2: Scan for it
uv run espro scan 127.0.0.1/32
```

The mock implements the ESPHome Native API (plaintext) with a single switch entity—useful for development without real hardware.

**Config locations:**
- Config file: `~/.config/espro/config.toml` (override with `ESPRO_CONFIG`)
- Data directory: `~/.local/share/espro`


## License

MIT License - see LICENSE file for details.
