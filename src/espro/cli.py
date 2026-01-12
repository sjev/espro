"""CLI for espro."""

import typer

from espro import __version__

app = typer.Typer(help="ESPro - Professional ESPHome infrastructure manager")
devices_app = typer.Typer(help="Device management commands")
app.add_typer(devices_app, name="devices")


def version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        typer.echo(f"espro version {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False,
        "--version",
        "-v",
        help="Show version and exit",
        callback=version_callback,
        is_eager=True,
    ),
) -> None:
    """ESPro CLI."""
    pass


@devices_app.command("scan")
def devices_scan() -> None:
    """Scan network for ESPHome devices."""
    typer.echo("Scanning for ESPHome devices...")
    typer.echo("(scan functionality not yet implemented)")


if __name__ == "__main__":
    app()
