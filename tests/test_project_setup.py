"""Tests for the AcoustiSense project foundation."""

from __future__ import annotations

from acoustisense.cli import main
from acoustisense.config.settings import get_settings


def test_settings_load_project_defaults() -> None:
    settings = get_settings()

    assert settings.project_name == "AcoustiSense"
    assert settings.log_level == "INFO"
    assert settings.data_dir.name == "datasets"
    assert settings.artifacts_dir.name == "artifacts"


def test_environment_overrides_yaml_settings(monkeypatch) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("ACOUSTISENSE_LOG_LEVEL", "DEBUG")
    try:
        assert get_settings().log_level == "DEBUG"
    finally:
        get_settings.cache_clear()


def test_cli_confirms_configuration(capsys) -> None:
    get_settings.cache_clear()
    try:
        assert main(["--check"]) == 0
    finally:
        get_settings.cache_clear()

    assert "configuration is valid" in capsys.readouterr().out
