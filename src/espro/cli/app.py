from __future__ import annotations

from typing import Annotated

import typer

from espro.utils.log_setup import setup_logging

from .commands import config as config_cmd
from .commands.device_logs import register as register_logs
from .commands.devices import register as register_devices
from .commands.info import register as register_info
from .commands.init import register as register_init
from .commands.mock import register as register_mock
from .commands.scan import register as register_scan
from .commands.validate import register as register_validate

app = typer.Typer(
    help="ESPro - Professional ESPHome infrastructure manager", no_args_is_help=True
)

app.add_typer(config_cmd.app, name="config")

register_init(app)
register_scan(app)
register_devices(app)
register_info(app)
register_validate(app)
register_mock(app)
register_logs(app)


@app.callback(invoke_without_command=True)
def main(
    version: Annotated[
        bool,
        typer.Option("--version", "-v", help="Show version and exit"),
    ] = False,
) -> None:
    """ESPro CLI."""
    setup_logging()

    if version:
        from importlib.metadata import version as get_version

        typer.echo(f"espro version {get_version('espro')}")
        raise typer.Exit()
