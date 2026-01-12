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
