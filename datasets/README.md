# Dataset storage

Keep dataset archives outside Git. Once you obtain the relevant official
DCASE 2021 Task 2 development ZIP archives and extract them yourself, pass the
extracted root to the inspector. A typical combined layout is
`datasets/raw/dcase2021/dev_data/fan/...` and
`datasets/raw/dcase2021/dev_data/pump/...`; inspect the actual extracted layout
before relying on it.

The project does not download or extract datasets. The inspector can list WAV
members in ZIP archives without extraction, but it does not export a manifest
from an archive because those paths may not exist on disk.

Derived data belongs under `datasets/processed/`. Raw and processed data are
excluded from Git. Read [the dataset protocol](../docs/dataset_protocol.md)
before acquiring or using the data.
