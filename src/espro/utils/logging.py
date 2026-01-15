from __future__ import annotations

import logging
import os
from typing import Literal

import coloredlogs  # type: ignore[import]

LogLevel = Literal["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"]

DEFAULT_FORMAT = "%(asctime)s %(name)s %(levelname)s %(message)s"
DEFAULT_DATE_FORMAT = "%H:%M:%S"


def setup_logging(level: LogLevel | None = None) -> None:
    resolved = (level or os.environ.get("LOGLEVEL", "INFO")).upper()

    coloredlogs.install(
        level=resolved,
        fmt=DEFAULT_FORMAT,
        datefmt=DEFAULT_DATE_FORMAT,
    )

    logging.getLogger("aioesphomeapi").setLevel(logging.WARNING)
