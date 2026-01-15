"""Tests for the public API."""

from __future__ import annotations

from typer.testing import CliRunner

from espro import __version__
from espro.cli.app import app

runner = CliRunner()


def test_version():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert f"espro version {__version__}" in result.stdout
