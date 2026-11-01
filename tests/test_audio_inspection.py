"""Tests for uploaded WAV validation and exploratory visualization data."""

from __future__ import annotations

from io import BytesIO

import numpy as np
import pytest
import soundfile as sf

from acoustisense.audio.inspection import (
    MAX_UPLOAD_BYTES,
    AudioInspectionError,
    inspect_uploaded_audio,
    prepare_spectrogram,
    prepare_waveform,
)


def make_wav(
    samples: np.ndarray,
    sample_rate: int = 16_000,
) -> bytes:
    """Encode small test-only PCM samples into an in-memory WAV container."""
    buffer = BytesIO()
    channel_count = 1 if samples.ndim == 1 else samples.shape[1]
    with sf.SoundFile(
        buffer,
        mode="w",
        samplerate=sample_rate,
        channels=channel_count,
        format="WAV",
        subtype="PCM_16",
    ) as wav_file:
        wav_file.write(samples)
    return buffer.getvalue()


def test_inspect_valid_mono_wav_and_metadata() -> None:
    samples = np.linspace(-0.75, 0.75, 1_600, dtype=np.float32)
    recording = inspect_uploaded_audio(make_wav(samples), "fan.wav")

    assert recording.filename == "fan.wav"
    assert recording.sample_rate == 16_000
    assert recording.num_channels == 1
    assert recording.num_samples == 1_600
    assert recording.duration_seconds == pytest.approx(0.1)
    assert recording.peak_amplitude == pytest.approx(0.75, abs=1 / 32768)
    assert recording.rms_energy == pytest.approx(
        np.sqrt(np.mean(np.square(samples, dtype=np.float64))),
        abs=1 / 32768,
    )


def test_inspect_valid_stereo_wav() -> None:
    samples = np.column_stack(
        (
            np.full(800, 0.25, dtype=np.float32),
            np.full(800, -0.5, dtype=np.float32),
        )
    )
    recording = inspect_uploaded_audio(make_wav(samples), "pump.wav")

    assert recording.num_channels == 2
    assert recording.samples.shape == (800, 2)
    assert recording.peak_amplitude == pytest.approx(0.5, abs=1 / 32768)


def test_wav_container_without_audio_frames_is_rejected() -> None:
    buffer = BytesIO()
    with sf.SoundFile(
        buffer,
        mode="w",
        samplerate=16_000,
        channels=1,
        format="WAV",
        subtype="PCM_16",
    ):
        pass

    with pytest.raises(AudioInspectionError, match="contains no audio samples"):
        inspect_uploaded_audio(buffer.getvalue(), "empty-audio.wav")


@pytest.mark.parametrize(
    ("payload", "filename", "message"),
    [
        (b"", "empty.wav", "empty"),
        (b"not a wav file", "corrupt.wav", "not a supported WAV"),
        (make_wav(np.zeros(16, dtype=np.float32)), "audio.flac", "Unsupported file type"),
    ],
)
def test_invalid_uploads_are_rejected(payload: bytes, filename: str, message: str) -> None:
    with pytest.raises(AudioInspectionError, match=message):
        inspect_uploaded_audio(payload, filename)


def test_corrupt_wav_data_is_reported() -> None:
    payload = bytearray(make_wav(np.zeros(64, dtype=np.float32)))
    payload[12:] = b"\x00" * (len(payload) - 12)
    with pytest.raises(AudioInspectionError):
        inspect_uploaded_audio(bytes(payload), "corrupt.wav")


def test_unsupported_container_with_wav_extension_is_rejected() -> None:
    with pytest.raises(AudioInspectionError, match="not a supported WAV"):
        inspect_uploaded_audio(b"fLaC" + b"\x00" * 20, "audio.wav")


def test_upload_size_limit_is_checked_before_decode() -> None:
    with pytest.raises(AudioInspectionError, match="25 MB upload limit"):
        inspect_uploaded_audio(b"x" * (MAX_UPLOAD_BYTES + 1), "large.wav")


def test_waveform_preparation_returns_time_and_selected_channel() -> None:
    samples = np.column_stack(
        (
            np.zeros(400, dtype=np.float32),
            np.full(400, 0.5, dtype=np.float32),
        )
    )
    recording = inspect_uploaded_audio(make_wav(samples), "stereo.wav")

    times, amplitudes = prepare_waveform(recording, channel_index=1)

    assert len(times) == len(amplitudes) == 400
    assert times[0] == 0
    assert times[-1] == pytest.approx(399 / recording.sample_rate)
    assert np.all(amplitudes > 0.49)


def test_waveform_downsampling_is_bounded_and_preserves_peaks() -> None:
    samples = np.zeros(20_000, dtype=np.float32)
    samples[12_345] = 0.9
    recording = inspect_uploaded_audio(make_wav(samples), "long.wav")

    times, amplitudes = prepare_waveform(recording, channel_index=0, max_points=200)

    assert len(times) <= 200
    assert np.max(amplitudes) == pytest.approx(0.9, abs=1 / 32768)
    assert np.all(np.diff(times) >= 0)


def test_waveform_channel_selection_is_validated() -> None:
    recording = inspect_uploaded_audio(make_wav(np.zeros((10, 2), dtype=np.float32)), "stereo.wav")

    with pytest.raises(ValueError, match="channel_index"):
        prepare_waveform(recording, channel_index=2)


def test_spectrogram_is_computed_from_selected_channel() -> None:
    samples = np.column_stack(
        (
            np.zeros(2_048, dtype=np.float32),
            np.sin(np.linspace(0, 40 * np.pi, 2_048, dtype=np.float32)),
        )
    )
    recording = inspect_uploaded_audio(make_wav(samples), "stereo.wav")

    frequencies, times, power_db = prepare_spectrogram(recording, channel_index=1)

    assert frequencies.ndim == times.ndim == 1
    assert power_db.shape == (len(frequencies), len(times))
    assert len(times) > 0
    assert np.isfinite(power_db).all()


def test_short_recording_reports_spectrogram_limitation() -> None:
    recording = inspect_uploaded_audio(make_wav(np.array([0.1], dtype=np.float32)), "short.wav")

    with pytest.raises(AudioInspectionError, match="At least two"):
        prepare_spectrogram(recording, channel_index=0)
