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
- **Run tests**: `uv run pytest`
- **Run tests with coverage**: `uv run invoke test`

### Maintenance
- **Clean untracked files**: `uv run invoke clean` (interactive)
- **Version bumping**: `uv run bump-my-version bump [patch|minor|major]`

## Project Structure

```
src/espro/
├── __init__.py              # Package initialization
├── cli.py                   # Typer-based CLI
├── core.py                  # Core functionality
└── py.typed                 # Type hints marker

tests/
└── test_espro.py            # Test suite
```

## Development Notes

- Uses Python 3.12+ with modern type hints
- Configured with ruff for linting/formatting and mypy for type checking
- Built with uv for dependency management
- Includes invoke tasks for common operations