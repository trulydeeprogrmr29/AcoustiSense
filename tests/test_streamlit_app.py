"""In-process smoke tests for the Streamlit application shell."""

from __future__ import annotations

from pathlib import Path

from streamlit.testing.v1 import AppTest


def test_app_shows_pending_model_status_and_machine_selector() -> None:
    app_path = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "acoustisense"
        / "ui"
        / "streamlit_app.py"
    )
    app = AppTest.from_file(str(app_path), default_timeout=10).run()

    assert not app.exception
    assert app.title[0].value == "AcoustiSense"
    assert app.selectbox[0].options == ["Fan", "Pump"]
    assert app.button[0].label == "Analyze recording"
    assert app.button[0].disabled
    assert any("Model integration pending" in item.value for item in app.info)

    app.selectbox[0].select("Pump").run()

    assert not app.exception
    assert any(metric.value == "Pump" for metric in app.metric)
