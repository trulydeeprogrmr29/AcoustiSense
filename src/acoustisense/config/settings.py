"""Validated application settings loaded from YAML and environment variables."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


def _read_yaml_settings() -> dict[str, Any]:
    default_path = Path(__file__).resolve().parents[3] / "configs" / "default.yaml"

    with default_path.open(encoding="utf-8") as config_file:
        contents = yaml.safe_load(config_file)

    if contents is None:
        return {}
    if not isinstance(contents, dict):
        raise ValueError(f"Configuration in {default_path} must be a YAML mapping.")
    return contents


class Settings(BaseSettings):
    """Settings shared by application components."""

    model_config = SettingsConfigDict(
        env_prefix="ACOUSTISENSE_",
        env_file=".env",
        extra="ignore",
    )

    project_name: str = "AcoustiSense"
    log_level: LogLevel = "INFO"
    data_dir: Path = Path("datasets")
    artifacts_dir: Path = Path("artifacts")

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """Use explicit constructor and environment values before the YAML defaults."""
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            file_secret_settings,
            _read_yaml_settings,
        )


@lru_cache
def get_settings() -> Settings:
    """Return the cached application settings."""
    return Settings()
