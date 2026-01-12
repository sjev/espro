import logging
import os
from typing import Literal

import coloredlogs  # type: ignore[import]

LogLevel = Literal["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"]


TIME_FORMAT = "%H:%M:%S.%f"


class LogFormat:
    """Predefined log formats."""

    DETAILED = "%(asctime)s [%(name)s] %(filename)s:%(lineno)d - %(message)s"
    SIMPLE = "%(asctime)s [%(levelname)s] %(message)s"


def setup_logging(
    loglevel: LogLevel | None = None, log_format: str = LogFormat.SIMPLE
) -> None:
    """Setup logging with coloredlogs."""
    if loglevel is None:
        lvl = os.environ.get("LOGLEVEL", "INFO").upper()
    else:
        lvl = loglevel.upper()
    coloredlogs.install(level=lvl, fmt=log_format, datefmt=TIME_FORMAT)
    logging.info(f"Log level set to {lvl}")


def suppress_logger(name: str, level: LogLevel = "ERROR") -> None:
    """Suppress a noisy library logger."""
    logging.getLogger(name).setLevel(level)
