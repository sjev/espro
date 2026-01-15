from __future__ import annotations

import asyncio
from datetime import datetime

import aioesphomeapi
import typer
from rich.console import Console
from rich.text import Text

LOG_LEVELS = {
    "none": aioesphomeapi.LogLevel.LOG_LEVEL_NONE,
    "error": aioesphomeapi.LogLevel.LOG_LEVEL_ERROR,
    "warn": aioesphomeapi.LogLevel.LOG_LEVEL_WARN,
    "info": aioesphomeapi.LogLevel.LOG_LEVEL_INFO,
    "config": aioesphomeapi.LogLevel.LOG_LEVEL_CONFIG,
    "debug": aioesphomeapi.LogLevel.LOG_LEVEL_DEBUG,
    "verbose": aioesphomeapi.LogLevel.LOG_LEVEL_VERBOSE,
    "very_verbose": aioesphomeapi.LogLevel.LOG_LEVEL_VERY_VERBOSE,
}


async def _subscribe_logs(
    host: str,
    port: int,
    level: aioesphomeapi.LogLevel,
    dump_config: bool,
    console: Console,
) -> None:
    client = aioesphomeapi.APIClient(host, port=port, password=None)
    await client.connect(login=True)

    info = await client.device_info()
    console.print(f"Connected to [green]{info.name}[/green] ({host}:{port})\n")

    stop_event = asyncio.Event()
    parser = aioesphomeapi.LogParser(strip_ansi_escapes=False)

    def _coerce_log_message(message: object) -> str:
        if isinstance(message, (bytes, bytearray, memoryview)):
            return bytes(message).decode("utf-8", errors="backslashreplace")
        return str(message)

    def on_log(msg: object) -> None:
        text = _coerce_log_message(getattr(msg, "message", ""))
        timestamp = datetime.now().strftime("%H:%M:%S")
        for line in text.splitlines():
            formatted = parser.parse_line(line, timestamp)
            if formatted:
                console.print(
                    Text.from_ansi(formatted), highlight=False, soft_wrap=True
                )

    client.subscribe_logs(on_log, log_level=level, dump_config=dump_config)

    try:
        await stop_event.wait()
    except asyncio.CancelledError:
        pass
    finally:
        await client.disconnect()


def register(app: typer.Typer) -> None:
    @app.command()
    def logs(
        host: str = typer.Argument(..., help="Device hostname or IP address"),
        port: int = typer.Option(6053, "--port", "-p", help="Port to connect to"),
        level: str = typer.Option("debug", "--level", "-l", help="Log level filter"),
        dump_config: bool = typer.Option(
            True,
            "--dump-config/--no-dump-config",
            help="Request the device to dump its config when subscribing",
        ),
    ) -> None:
        """Stream logs from an ESPHome device."""
        console = Console()

        log_level = LOG_LEVELS.get(level.lower())
        if log_level is None:
            console.print(f"[red]Invalid log level:[/red] {level}")
            console.print(f"Valid levels: {', '.join(LOG_LEVELS.keys())}")
            raise typer.Exit(1)

        console.print(f"Connecting to {host}:{port}...")
        console.print("Press Ctrl+C to stop.\n")

        try:
            asyncio.run(_subscribe_logs(host, port, log_level, dump_config, console))
        except KeyboardInterrupt:
            console.print("\n[green]Disconnected.[/green]")
        except (
            aioesphomeapi.APIConnectionError,
            aioesphomeapi.InvalidAuthAPIError,
            ConnectionError,
            OSError,
            TimeoutError,
        ) as exc:
            console.print(f"[red]Error:[/red] {exc}")
            raise typer.Exit(1) from None
