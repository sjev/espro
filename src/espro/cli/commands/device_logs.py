from __future__ import annotations

import asyncio
from datetime import datetime

import aioesphomeapi as api
import typer
from rich.console import Console
from rich.text import Text


def _parse_log_level(value: str) -> api.LogLevel:
    normalized = value.strip().upper()
    if not normalized:
        raise KeyError(value)
    if not normalized.startswith("LOG_LEVEL_"):
        normalized = f"LOG_LEVEL_{normalized}"
    return api.LogLevel[normalized]


def _log_level_names() -> list[str]:
    return [
        level.name.removeprefix("LOG_LEVEL_").lower()
        for level in sorted(api.LogLevel, key=lambda item: item.value)
    ]


async def _subscribe_logs(
    host: str,
    port: int,
    level: api.LogLevel,
    dump_config: bool,
    console: Console,
) -> None:
    client = api.APIClient(host, port=port, password=None)
    await client.connect(login=True)

    info = await client.device_info()
    console.print(f"Connected to [green]{info.name}[/green] ({host}:{port})\n")

    stop_event = asyncio.Event()
    parser = api.LogParser(strip_ansi_escapes=False)

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

    try:
        log_level = _parse_log_level(level)
    except KeyError:
        console.print(f"[red]Invalid log level:[/red] {level}")
        console.print(f"Valid levels: {', '.join(_log_level_names())}")
        raise typer.Exit(1) from None

    console.print(f"Connecting to {host}:{port}...")
    console.print("Press Ctrl+C to stop.\n")

    try:
        asyncio.run(_subscribe_logs(host, port, log_level, dump_config, console))
    except KeyboardInterrupt:
        console.print("\n[green]Disconnected.[/green]")
    except (
        api.APIConnectionError,
        api.InvalidAuthAPIError,
        ConnectionError,
        OSError,
        TimeoutError,
    ) as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from None


def register(app: typer.Typer) -> None:
    app.command()(logs)
