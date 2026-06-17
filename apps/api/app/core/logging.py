"""Loguru-based logging configuration.

`configure_logging()` is called once at app startup. It resets Loguru's default
handler and installs a single stderr sink at the configured level.
"""

import sys

from loguru import logger

from app.core.config import settings


def configure_logging(level: str | None = None) -> None:
    """Configure the global Loguru logger.

    Args:
        level: Override for the log level; defaults to `settings.log_level`.
    """
    logger.remove()
    logger.add(
        sys.stderr,
        level=(level or settings.log_level).upper(),
        backtrace=False,
        diagnose=False,
        enqueue=True,
    )


__all__ = ["configure_logging", "logger"]
