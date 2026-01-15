# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

`espro` is a control plane for ESPHome device fleets. It provides a logical device registry that decouples device identity from physical hardware, solving the "device replacement breaks everything" problem.

## Current Scope

**Implemented (Phase 1: Registry)**
- Network scanning via `aioesphomeapi` (async, concurrent)
- Logical ↔ physical device mapping in TOML
- Mapping validation (detect drift, missing devices)
- Mock ESPHome device for testing without hardware

**Not yet implemented**
- MQTT bridge (Phase 2)
- Home Assistant integration (Phase 2)
- Firmware deployment (Phase 3)
- Fleet operations (Phase 3)

## Design Decisions

**Why TOML for storage?**
- Human-readable and editable
- Git-friendly (diffable, mergeable)
- No database dependencies
- Matches "infrastructure as code" philosophy

**Why logical/physical split?**
- Physical devices are identified by mDNS hostname (e.g., `esp-kitchen.local`)
- Logical devices are stable identifiers chosen by the user (e.g., `kitchen_sensor`)
- When hardware fails, only the mapping changes—not downstream references

**Why async scanning?**
- Network scanning is I/O-bound
- Concurrent checks reduce scan time from minutes to seconds
- Uses `asyncio.gather()` with semaphore for controlled parallelism

**Why frozen Pydantic models?**
- Immutable configuration prevents accidental mutation
- Validation at load time catches errors early
- Clear separation between config (immutable) and state (mutable)

**Why separate CLI and commands?**
- CLI layer (`cli/`) handles user interaction (Typer, Rich output)
- Commands layer (`commands/`) contains business logic (pure functions)
- Enables testing commands without CLI overhead

## Development Commands

### Setup
```bash
uv sync --group dev
```

### Code Quality
- **Linting and formatting**: `uv run ruff check` and `uv run ruff format`
- **Type checking**: `uv run mypy src`
- **Combined linting**: `uv run invoke lint`

### Testing
- **Run all tests**: `uv run pytest`
- **Run specific test**: `uv run pytest -k test_name`
- **Run with coverage**: `uv run invoke test`

### Maintenance
- **Clean untracked files**: `uv run invoke clean` (interactive)

## Project Structure

```
src/espro/
├── __init__.py              # Public API exports + version
├── cli/                     # Typer CLI entrypoint and commands
├── commands/                # Core command implementations
├── config/                  # Settings + XDG path resolution
├── models/                  # Pydantic data models
├── storage/                 # File-based persistence
├── utils/                   # Logging helpers
└── py.typed                 # Type hints marker

tests/
├── conftest.py              # Shared fixtures
├── test_public.py           # Public API tests
└── test_internals.py        # Internal module tests
```

## Architecture

### Device Discovery (commands/scan.py)
- Uses `aioesphomeapi` to communicate with ESPHome devices on port 6053
- `scan_network()`: Async concurrent scanning of CIDR ranges
- `detect_local_network()`: Auto-detects local /24 subnet
- Returns `PhysicalDevice` pydantic model

### Config (config/)
- TOML config at `~/.config/espro/config.toml` (override with `ESPRO_CONFIG`)
- Settings are frozen Pydantic models

### Storage (storage/database.py)
- Stores logical registry in `devices.toml`
- Stores scan result JSON in `physical/current.json`
- Data directory defaults to `~/.local/share/espro`

### CLI Structure (cli/app.py)
- Built with Typer and Rich for formatted output
- Commands: `config init`, `scan`, `list`, `add`, `remove`, `info`, `validate`, `logs`, `mock`

### Logging (utils/logging.py)
- Uses `coloredlogs` for colored terminal output
- Log level controlled by `LOGLEVEL` environment variable (default: INFO)
- Suppresses noisy `aioesphomeapi` logs by default

## Development Notes

- Uses Python 3.12+ with modern type hints (PEP 604 unions)
- Configured with ruff for linting/formatting and mypy for type checking
- Built with uv for dependency management
- Async-first design using asyncio
- Includes invoke tasks for common operations

## Known Limitations (Prototype)

- No MQTT bridge yet (devices are registered but not exposed)
- Scanning requires devices to have ESPHome Native API enabled (port 6053)
- No authentication support for encrypted ESPHome devices
- Mock device implements plaintext API only
- No persistence of scan history (only latest scan stored)
