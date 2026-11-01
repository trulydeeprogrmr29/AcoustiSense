# Architecture

## Prototype boundary

The local prototype will use Streamlit as its only application framework.
There is no separate backend server or frontend application.

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

Model training is planned for Google Colab. The locally trained-and-exported
model weights and configuration will later be integrated for lightweight CPU
inference. This foundation does not implement Streamlit, preprocessing, or
model training.

## Dataset interface

The DCASE 2021 Task 2 development data is the initial source for the fan and
pump categories, sections 00-02. `scripts/inspect_dataset.py` exports a
root-relative CSV manifest with a stable nine-column contract so future
training code can consume the same file inventory.

The manifest records section, domain, partition, and condition separately.
Source-test and target-test recordings remain distinct. Dataset inspection
does not decode audio, extract archives, or infer metadata absent from filenames
and directories.

## Research safeguards

- Keep training, validation, and test data separated; do not calibrate
  thresholds with test data.
- Preserve machine, section, source/target domain, and partition distinctions.
- Treat the published per-section recording counts as approximate; report
  counts found in the actual dataset.
- Record preprocessing and configuration with each experiment.
- Keep datasets and generated checkpoints outside source control.
- Report anomaly detection and supported fault diagnosis only; do not claim
  remaining useful life or exact future failure times.
