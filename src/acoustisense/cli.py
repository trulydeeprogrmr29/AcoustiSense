"""Command-line entry point for basic application setup checks."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

import yaml
from pydantic import ValidationError

from acoustisense.config.settings import get_settings
from acoustisense.core.logging import configure_logging


def main(argv: Sequence[str] | None = None) -> int:
    """Load settings and report whether the application is configured."""
    parser = argparse.ArgumentParser(description="Check the AcoustiSense project configuration.")
    parser.add_argument(
        "--check",
        action="store_true",
        help="validate configuration (also the default action)",
    )
    parser.parse_args(argv)

    try:
        settings = get_settings()
    except (OSError, ValidationError, yaml.YAMLError, ValueError) as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 1

    logger = configure_logging(settings)
    logger.info("Configuration loaded successfully.")
    print(
        f"{settings.project_name} configuration is valid. "
        f"Data directory: {settings.data_dir}; artifacts directory: {settings.artifacts_dir}"
    )
    return 0
