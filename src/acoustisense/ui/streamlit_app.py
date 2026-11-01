"""Streamlit shell for in-memory industrial audio inspection."""

from __future__ import annotations

import matplotlib.pyplot as plt
import streamlit as st

from acoustisense.audio.inspection import (
    AudioInspectionError,
    AudioRecording,
    inspect_uploaded_audio,
    prepare_spectrogram,
    prepare_waveform,
)

_EXPECTED_SAMPLE_RATE = 16_000
_EXPECTED_DURATION_SECONDS = 10.0
_DURATION_TOLERANCE_SECONDS = 1.0

st.set_page_config(
    page_title="AcoustiSense | Acoustic Condition Monitoring",
    page_icon="🔊",
    layout="wide",
)


def _render_header() -> None:
    st.title("AcoustiSense")
    st.subheader("Intelligent Acoustic Condition Monitoring for Industrial Machinery.")
    st.caption(
        "Inspect machine recordings and their acoustic characteristics. "
        "Anomaly analysis will be available after the approved model is integrated."
    )


def _render_status(machine_type: str) -> None:
    overview = st.columns(3)
    overview[0].metric("Selected machine", machine_type)
    overview[1].metric("Model integration", "Pending")
    overview[2].metric("Dataset / experiments", "Research phase")

    st.info("Model integration pending — trained model is not yet available.")
    st.button(
        "Analyze recording",
        disabled=True,
        help="Analysis will be enabled after the approved model and preprocessing are integrated.",
        width="content",
    )


def _render_metadata(recording: AudioRecording) -> None:
    metadata = st.columns(4)
    metadata[0].metric("Sample rate", f"{recording.sample_rate:,} Hz")
    metadata[1].metric("Channels", str(recording.num_channels))
    metadata[2].metric("Duration", f"{recording.duration_seconds:.2f} s")
    metadata[3].metric("Samples", f"{recording.num_samples:,}")

    measurements = st.columns(3)
    measurements[0].metric("Peak amplitude", f"{recording.peak_amplitude:.5f}")
    measurements[1].metric("RMS energy", f"{recording.rms_energy:.5f}")
    measurements[2].metric("Filename", recording.filename)

    if recording.sample_rate != _EXPECTED_SAMPLE_RATE:
        st.warning(
            f"This recording is {recording.sample_rate:,} Hz. "
            f"The DCASE development format uses {_EXPECTED_SAMPLE_RATE:,} Hz."
        )
    if recording.num_channels != 1:
        st.warning(
            f"This recording has {recording.num_channels} channels. "
            "The DCASE development format is mono."
        )
    if abs(recording.duration_seconds - _EXPECTED_DURATION_SECONDS) > _DURATION_TOLERANCE_SECONDS:
        st.warning(
            f"This recording is {recording.duration_seconds:.2f} seconds. "
            "DCASE development clips are approximately 10 seconds."
        )


def _render_waveform(recording: AudioRecording, channel_index: int) -> None:
    times, amplitudes = prepare_waveform(recording, channel_index)
    figure, axis = plt.subplots(figsize=(10, 3.2))
    try:
        axis.plot(times, amplitudes, linewidth=0.7, color="#187a78")
        axis.set_title(f"Waveform — Channel {channel_index + 1}")
        axis.set_xlabel("Time (seconds)")
        axis.set_ylabel("Amplitude")
        axis.grid(True, alpha=0.2)
        figure.tight_layout()
        st.pyplot(
            figure,
            clear_figure=True,
            alt=f"Amplitude waveform for channel {channel_index + 1} over time.",
        )
    finally:
        plt.close(figure)


def _render_spectrogram(recording: AudioRecording, channel_index: int) -> None:
    try:
        frequencies, times, power_db = prepare_spectrogram(recording, channel_index)
    except AudioInspectionError as exc:
        st.info(str(exc))
        return

    figure, axis = plt.subplots(figsize=(10, 4))
    try:
        image = axis.pcolormesh(
            times,
            frequencies,
            power_db,
            shading="auto",
            cmap="magma",
        )
        axis.set_title(f"Exploratory spectrogram — Channel {channel_index + 1}")
        axis.set_xlabel("Time (seconds)")
        axis.set_ylabel("Frequency (Hz)")
        figure.colorbar(image, ax=axis, label="Power (dB)")
        figure.tight_layout()
        st.pyplot(
            figure,
            clear_figure=True,
            alt=f"Exploratory time-frequency spectrogram for channel {channel_index + 1}.",
        )
    finally:
        plt.close(figure)


def main() -> None:
    """Render the application and inspect uploaded WAV recordings."""
    with st.sidebar:
        st.markdown("## AcoustiSense")
        st.caption("Industrial acoustic monitoring")
        machine_type = st.selectbox("Machine category", ("Fan", "Pump"))
        st.divider()
        st.markdown("**Application status**")
        st.success("Audio inspection available")
        st.warning("Model integration pending")

    _render_header()

    with st.container(border=True):
        st.subheader("Monitoring overview")
        st.write(
            f"Selected category: **{machine_type}**. This selection is for the future "
            "analysis workflow; it does not indicate that a model has been trained."
        )
        _render_status(machine_type)

    st.subheader("Inspect a machine recording")
    uploaded_file = st.file_uploader(
        "Upload a WAV recording",
        type=["wav"],
        max_upload_size=25,
        help="Maximum file size: 25 MB. The recording is inspected in memory and is not saved.",
    )
    if uploaded_file is None:
        st.info("Upload a WAV file to view its metadata, playback, waveform, and spectrogram.")
        return

    payload = uploaded_file.getvalue()
    try:
        recording = inspect_uploaded_audio(payload, uploaded_file.name)
    except AudioInspectionError as exc:
        st.error(str(exc))
        return

    st.markdown(f"**Recording:** `{recording.filename}`")
    _render_metadata(recording)

    st.subheader("Audio playback")
    st.audio(
        payload,
        format="audio/wav",
        alt=f"Audio playback for {recording.filename}.",
    )

    channel_labels = [f"Channel {index + 1}" for index in range(recording.num_channels)]
    selected_channel = st.selectbox(
        "Channel to visualize",
        options=range(recording.num_channels),
        format_func=lambda index: channel_labels[index],
    )

    waveform_tab, spectrogram_tab = st.tabs(("Waveform", "Exploratory spectrogram"))
    with waveform_tab:
        _render_waveform(recording, selected_channel)
    with spectrogram_tab:
        st.caption(
            "Exploratory time-frequency view only; this is not the final model's "
            "input representation."
        )
        _render_spectrogram(recording, selected_channel)


if __name__ == "__main__":
    main()
