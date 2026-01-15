# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

`espro` is a Python library for professional esphome infrastructure: manage devices without breaking entity ids, automations, or dashboards.

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
- Commands: init, scan, list, add, remove, info, validate, logs, mock

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
