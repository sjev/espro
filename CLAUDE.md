# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

`espro` is a Python library for professional esphome infrastructure: manage devices without breaking entity ids, automations, or dashboards.

## Development Commands

### Setup
```bash
uv sync
```

### Code Quality
- **Linting and formatting**: `uv run ruff check --fix` and `uv run ruff format`
- **Type checking**: `uv run mypy .`
- **Combined linting**: `uv run invoke lint`

### Testing
- **Run all tests**: `uv run pytest`
- **Run specific test**: `uv run pytest -k test_name`
- **Run with coverage**: `uv run invoke test`

### Build & Release
- **Build package**: `uv run invoke build-package`
- **Release to PyPI**: `uv run invoke release` (requires PYPI_TOKEN env var)

### Maintenance
- **Clean untracked files**: `uv run invoke clean` (interactive)
- **Version bumping**: `uv run bump-my-version bump [patch|minor|major]`

## Project Structure

```
src/espro/
├── __init__.py              # Package initialization
├── cli.py                   # Typer-based CLI with Rich output
├── core.py                  # Core functionality (placeholder)
├── scanner.py               # ESPHome device discovery
├── logging.py               # Logging configuration
└── py.typed                 # Type hints marker

tests/
└── test_espro.py            # Test suite
```

## Architecture

### Device Discovery (scanner.py)
- Uses `aioesphomeapi` to communicate with ESPHome devices on port 6053
- `scan_network()`: Async concurrent scanning of CIDR ranges
- `detect_local_network()`: Auto-detects local /24 subnet
- Returns `ESPHomeDevice` dataclass with device metadata

### CLI Structure (cli.py)
- Built with Typer for command hierarchy: `espro devices scan`
- Rich library for formatted table output
- Commands are grouped into sub-apps (e.g., `devices_app`)

### Logging (logging.py)
- Uses `coloredlogs` for colored terminal output
- Log level controlled by `LOGLEVEL` environment variable (default: INFO)
- Suppresses noisy `aioesphomeapi` logs by default

## Development Notes

- Uses Python 3.12+ with modern type hints (PEP 604 unions)
- Configured with ruff for linting/formatting and mypy for type checking
- Built with uv for dependency management
- Async-first design using asyncio
- Includes invoke tasks for common operations