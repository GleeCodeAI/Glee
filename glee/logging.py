"""Logging configuration for Glee."""

import sys
from typing import TYPE_CHECKING

from loguru import logger

if TYPE_CHECKING:
    from loguru import Logger


def setup_logging() -> "Logger":
    """Configure loguru logging."""
    logger.remove()

    logger.add(
        sys.stderr,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="DEBUG",
    )

    return logger
