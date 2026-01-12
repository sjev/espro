"""Tests for espro."""

from typer.testing import CliRunner

from espro import __version__
from espro.cli import app

runner = CliRunner()


def test_version():
    """Test version command."""
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert f"espro version {__version__}" in result.stdout


def test_version_short():
    """Test version command with short flag."""
    result = runner.invoke(app, ["-v"])
    assert result.exit_code == 0
    assert f"espro version {__version__}" in result.stdout


def test_devices_scan():
    """Test devices scan command."""
    result = runner.invoke(app, ["devices", "scan"])
    assert result.exit_code == 0
    assert "Scanning for ESPHome devices..." in result.stdout
