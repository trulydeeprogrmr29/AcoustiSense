# AcoustiSense

AcoustiSense is a research prototype for **acoustic anomaly detection in
industrial machinery**, initially focused on fans and pumps. The project aims
to detect deviations from normal machine sounds, including under changes in
operating or environmental conditions. It does not claim to predict remaining
useful life or exact future failure times.

## Current status

The local Streamlit prototype supports Fan/Pump selection and in-memory WAV
inspection: file validation, recording metadata, audio playback, a
peak-preserving waveform view, and an exploratory spectrogram. Uploads are
limited to 25 MB and are not written to disk or logged.

**Model integration is pending.** The trained model and approved preprocessing
configuration are not available yet. Analysis controls are disabled and the
application does not produce predictions or simulated health values.

The DCASE 2021 Task 2 dataset inspection utility remains available for local
file inventory and extracted-directory manifest export. Dataset acquisition
and GPU training will use Google Colab; no dataset is downloaded or extracted
by this application. At the last local dataset check, the `datasets/` folders
contained no WAV recordings. The real-audio UI check used a browser upload;
that recording was processed in memory and was not saved in the repository.

## Prototype architecture

Streamlit is the only planned application framework; there is no separate
backend server:

```text
Streamlit UI
    ↓
Audio preprocessing
    ↓
Trained PyTorch model
    ↓
Anomaly scoring
    ↓
Machine health results
```

Training is planned for Google Colab. Local development will integrate the
trained model and support lightweight CPU inference. Streamlit is installed
for the prototype; PyTorch and Librosa remain deferred until the model and
preprocessing contract are approved.

## Repository layout

```text
configs/                 Default application configuration
datasets/raw/            User-obtained source archives/recordings (not committed)
datasets/processed/      Derived data (not committed)
artifacts/                Model weights and generated outputs (not committed)
docs/                     Architecture and dataset protocol
experiments/              Experiment notes and configuration
scripts/                  Dataset inspection and maintenance tools
src/acoustisense/         Installable application package and shared settings
  audio/                  In-memory WAV inspection and chart data
  ui/                     Streamlit application
tests/                    Automated tests
```

The `src/` layout keeps imports consistent between development and installed
use. Future application components should stay modular; do not add a separate
API server or another UI framework.

## Dataset selection

The primary dataset is the **DCASE 2021 Challenge Task 2 development dataset**.
Initial scope is machine categories `fan` and `pump`, development sections
`00`, `01`, and `02`. MIMII DUE is a subset of the DCASE 2021 dataset, not an
independent dataset to download alongside it. See the [dataset protocol](docs/dataset_protocol.md)
for official sources, directory/filename conventions, splits, licensing, and
the manifest schema.

No WAV recordings or ZIP archives were found in the local `datasets/`
directory during the dataset setup check. Only the raw/processed placeholder
files and dataset instructions were present.

## Setup (Windows PowerShell)

Requirements: Python 3.11 or newer. Python 3.13.1 is the local development
interpreter. The current prototype uses Streamlit, NumPy, SoundFile, and
Matplotlib for CPU-only WAV inspection. It does not install PyTorch, Librosa,
or CUDA. From the project root:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

To use Python 3.11, replace `py -3.13` with `py -3.11`. If activation is
blocked by PowerShell's execution policy, use the venv interpreter directly:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

Copy `.env.example` to `.env` to override application settings.

## Run the Streamlit prototype

```powershell
python -m streamlit run src/acoustisense/ui/streamlit_app.py
```

The dashboard offers Fan/Pump selection, WAV upload, metadata and signal
measurements, playback, a selected-channel waveform, and an exploratory
spectrogram. The spectrogram is not represented as the eventual model input.
Warnings for sample rate, channel count, or duration are informational and do
not reject otherwise valid WAV recordings. Uploads are limited to 25 MB,
processed in memory, and not saved or logged.

### Real WAV upload check

The running app was checked with a real uploaded mono WAV. It decoded and
played successfully, displayed the waveform and exploratory spectrogram, and
reported sample rate, channel count, duration, sample count, peak amplitude,
and RMS energy. That recording was 48 kHz and about 17.9 seconds long, so the
app correctly displayed informational warnings for differing from the DCASE
development format (16 kHz, mono, approximately 10 seconds). The warnings do
not mean the file failed to load. No anomaly prediction was made.

## Inspect the dataset

After obtaining and extracting the official archives yourself, inspect the
extracted root and export a manifest:

```powershell
python scripts/inspect_dataset.py --root datasets/raw/dcase2021 --export-manifest datasets/manifests/dcase2021_manifest.csv
```

Inspect one or more archives without extracting them:

```powershell
python scripts/inspect_dataset.py --archive datasets/raw/dev_data_fan.zip datasets/raw/dev_data_pump.zip
```

ZIP inventory is not exported as a training manifest: archive member paths do
not guarantee files exist as extracted paths. The script does not read audio
samples, download data, or extract archives.

## Run tests and lint

```powershell
acoustisense --check
python -m pytest
python -m ruff check .
```

## Research and development phases

1. **Foundation and dataset reconnaissance** — project configuration, official
   protocol documentation, inventory utility, and stable manifest contract.
2. **Dataset integration** — inspect real files/metadata and establish
   protocol-compliant train/validation/test use.
3. **Model research** — finalize the inference/preprocessing contract, compare
   unsupervised baselines and deep-learning methods, and train on Colab with
   reproducible metrics.
4. **Noise/domain robustness** — evaluate source/target conditions without
   leaking test information into training or threshold calibration.
5. **Model integration** — integrate the approved model and exact
   preprocessing in the existing Streamlit prototype after its inference
   contract is finalized.

Do not fabricate results, treat approximate dataset counts as exact, or
describe synthetic tests as experiments on industrial recordings. The system's
initial aim is anomaly detection and only dataset-supported fault diagnosis.
