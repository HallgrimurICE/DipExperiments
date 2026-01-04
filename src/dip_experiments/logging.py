"""Logging helpers for DipExperiments."""

from __future__ import annotations

import logging
from typing import Optional

_DEFAULT_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"


def configure_logging(level: int = logging.INFO, format_string: str = _DEFAULT_FORMAT) -> None:
    """Configure global logging with a consistent format."""
    logging.basicConfig(level=level, format=format_string)


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Return a configured logger for the given name."""
    return logging.getLogger(name or __name__)
