# ESPro

*ESPro turns physical ESPHome devices into swappable infrastructure beneath stable logical identities.*



## The Problem

ESPHome ties device identity to physical hardware. When a broken device gets replaced:

- All Home Assistant entity IDs change
- Dashboards break
- Automations need manual updates
- 30+ minutes of recovery work per device

This tool aims to simplify device comissioning and management for professional installers and power users who want to treat home infrastructure as code.

## The Solution

**Hardware abstraction layer for ESPHome.**

Home Assistant connects to stable logical devices (`outdoor_light_1`), not physical hardware. When a device breaks, update a config file and restart—entity IDs stay stable, automations keep working.
```yaml
# config/devices.yaml
logical_devices:
  outdoor_light_1:
    physical: esp-sonoff-1.local

  chicken_scale:
    physical: esp32-coop.local
```

Device dies? Change the IP, reload ESPro mappings. Done.

## Architecture
```
Home Assistant (stable entity IDs)
    ↓
ESPro (device registry + proxy)
    ↓
Physical ESPHome Devices (swappable)
```

Three layers with clear responsibilities:

- **ESPHome** - Firmware and I/O
- **ESPro** - Hardware abstraction and lifecycle management
- **Home Assistant** - Automations and UI

## Philosophy

**Boring technology**: Docker, YAML, Git, REST—nothing exotic.

**Plain text wins**: Configuration in Git-tracked YAML. No database, ever. Audit trail via `git log`, rollback via `git revert`, backup via `git push`.

**Infrastructure as code**: Reproducible deployments. Version-controlled configuration. Offline-capable.

**Unix philosophy**: Do one thing well—provide hardware abstraction. Don't replace ESPHome or Home Assistant.

## Status

**Early development.** Validating technical feasibility and gathering community feedback.

Target audience: Professional installers managing 10-1000+ devices across single or multiple sites who need reproducible deployments and version stability.

## Questions?

This is a proof-of-concept. Feedback is welcome.

---


## Development

**Quick start:**
1. Install [uv](https://docs.astral.sh/uv/getting-started/installation/)
2. Install dependencies: `uv sync`
3. Run CLI: `uv run espro --help`
4. Run tests: `uv run pytest`

**Available invoke tasks** (optional, install with `uv tool install invoke`):
- `invoke lint` - Run ruff and mypy
- `invoke test` - Run tests with coverage
- `invoke clean` - Remove untracked files (interactive)


## License

MIT License - see LICENSE file for details.
