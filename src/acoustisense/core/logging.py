"""Centralized logging setup."""

from __future__ import annotations

import logging

from acoustisense.config.settings import Settings

_LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"


def configure_logging(settings: Settings) -> logging.Logger:
    """Configure the root logger once and return the application logger."""
    root_logger = logging.getLogger()
    if not root_logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(_LOG_FORMAT))
        root_logger.addHandler(handler)

    root_logger.setLevel(settings.log_level)
    return logging.getLogger("acoustisense")
