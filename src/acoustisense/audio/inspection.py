"""In-memory validation and exploratory visualization data for uploaded WAV audio."""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO

import numpy as np
import soundfile as sf
from matplotlib.mlab import specgram

MAX_UPLOAD_BYTES = 25 * 1024 * 1024
MAX_WAVEFORM_POINTS = 12_000
_WAV_CONTAINER_IDS = {b"RIFF", b"RIFX", b"RF64"}


class AudioInspectionError(ValueError):
    """Raised when an uploaded file cannot be inspected as usable WAV audio."""


@dataclass(frozen=True)
class AudioRecording:
    """Decoded audio samples and metadata for a single in-memory recording."""

    filename: str
    sample_rate: int
    samples: np.ndarray

    @property
    def num_samples(self) -> int:
        """Return the number of frames in the recording."""
        return int(self.samples.shape[0])

    @property
    def num_channels(self) -> int:
        """Return the number of audio channels."""
        return int(self.samples.shape[1])

    @property
    def duration_seconds(self) -> float:
        """Return recording duration in seconds."""
        return self.num_samples / self.sample_rate

    @property
    def peak_amplitude(self) -> float:
        """Return the maximum absolute sample value across channels."""
        return float(np.max(np.abs(self.samples)))

    @property
    def rms_energy(self) -> float:
        """Return the root-mean-square amplitude across all samples and channels."""
        return float(np.sqrt(np.mean(np.square(self.samples, dtype=np.float64))))


def inspect_uploaded_audio(
    payload: bytes,
    filename: str,
    max_bytes: int = MAX_UPLOAD_BYTES,
) -> AudioRecording:
    """Validate and decode an uploaded WAV from memory without writing it to disk."""
    if not filename.casefold().endswith(".wav"):
        raise AudioInspectionError("Unsupported file type. Please upload a .wav recording.")
    if not payload:
        raise AudioInspectionError("The uploaded file is empty.")
    if max_bytes <= 0:
        raise ValueError("max_bytes must be greater than zero.")
    if len(payload) > max_bytes:
        raise AudioInspectionError(
            f"File exceeds the {max_bytes // (1024 * 1024)} MB upload limit."
        )
    if (
        len(payload) < 12
        or payload[:4] not in _WAV_CONTAINER_IDS
        or payload[8:12] != b"WAVE"
    ):
        raise AudioInspectionError("The file is not a supported WAV audio recording.")

    try:
        samples, sample_rate = sf.read(
            BytesIO(payload),
            dtype="float32",
            always_2d=True,
        )
    except (OSError, RuntimeError, ValueError) as exc:
        raise AudioInspectionError(
            "The WAV file could not be decoded. It may be corrupted or use an unsupported codec."
        ) from exc

    if samples.size == 0 or samples.shape[0] == 0:
        raise AudioInspectionError("The WAV file contains no audio samples.")
    if sample_rate <= 0:
        raise AudioInspectionError("The WAV file has an invalid sample rate.")
    if not np.isfinite(samples).all():
        raise AudioInspectionError("The WAV recording contains non-finite sample values.")

    return AudioRecording(filename=filename, sample_rate=sample_rate, samples=samples)


def prepare_waveform(
    recording: AudioRecording,
    channel_index: int,
    max_points: int = MAX_WAVEFORM_POINTS,
) -> tuple[np.ndarray, np.ndarray]:
    """Return time and amplitude arrays, preserving local peaks when downsampling."""
    if not 0 <= channel_index < recording.num_channels:
        raise ValueError(f"channel_index must be between 0 and {recording.num_channels - 1}.")
    if max_points < 2:
        raise ValueError("max_points must be at least 2.")

    channel = recording.samples[:, channel_index]
    if channel.size <= max_points:
        indices = np.arange(channel.size, dtype=np.int64)
    else:
        bucket_count = max_points // 2
        edges = np.linspace(0, channel.size, num=bucket_count + 1, dtype=np.int64)
        selected_indices: list[int] = []
        for start, end in zip(edges[:-1], edges[1:], strict=True):
            block = channel[start:end]
            low_index = int(start + np.argmin(block))
            high_index = int(start + np.argmax(block))
            selected_indices.extend(sorted({low_index, high_index}))
        indices = np.asarray(selected_indices, dtype=np.int64)

    times = indices.astype(np.float64) / recording.sample_rate
    return times, channel[indices]


def prepare_spectrogram(
    recording: AudioRecording,
    channel_index: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return frequency, time, and power-in-decibels arrays for an exploratory spectrogram."""
    if not 0 <= channel_index < recording.num_channels:
        raise ValueError(f"channel_index must be between 0 and {recording.num_channels - 1}.")

    channel = recording.samples[:, channel_index]
    if channel.size < 2:
        raise AudioInspectionError("At least two audio samples are needed for a spectrogram.")

    n_fft = min(1024, channel.size)
    power, frequencies, times = specgram(
        channel,
        NFFT=n_fft,
        Fs=recording.sample_rate,
        noverlap=n_fft // 2,
        mode="psd",
        scale_by_freq=True,
    )
    power_db = 10 * np.log10(np.maximum(power, np.finfo(np.float64).tiny))
    return frequencies, times, power_db
