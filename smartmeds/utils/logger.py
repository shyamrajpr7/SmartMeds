"""
Logging configuration for SmartMeds.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

LOG_DIR = Path.home() / ".smartmeds" / "logs"
LOG_FILE = LOG_DIR / "smartmeds.log"

_configured = False


def configure_logging(level: int = logging.INFO, log_to_file: bool = True) -> None:
    """
    Configure the application-wide logging setup.

    Args:
        level: Logging level (e.g., logging.DEBUG, logging.INFO).
        log_to_file: Whether to also write logs to a file.
    """
    global _configured
    if _configured:
        return

    handlers: list[logging.Handler] = [
        logging.StreamHandler(sys.stdout),
    ]

    if log_to_file:
        try:
            LOG_DIR.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
            file_handler.setLevel(level)
            handlers.append(file_handler)
        except OSError:
            pass

    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=handlers,
    )
    _configured = True


def get_logger(name: str) -> logging.Logger:
    """
    Get a named logger, configuring logging if not already done.

    Args:
        name: Logger name (typically __name__).

    Returns:
        A configured Logger instance.
    """
    configure_logging()
    return logging.getLogger(name)
