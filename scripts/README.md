# Scripts

## Inspect DCASE dataset files

Inspect an extracted dataset and export the shared manifest:

```powershell
python scripts/inspect_dataset.py --root datasets/raw/dcase2021 --export-manifest datasets/manifests/dcase2021_manifest.csv
```

Inventory one or more ZIP files without extracting them:

```powershell
python scripts/inspect_dataset.py --archive datasets/raw/dev_data_fan.zip datasets/raw/dev_data_pump.zip
```

The script uses Python's standard library. It lists files and metadata only; it
does not read audio samples, download data, or extract archives. See
[`dataset_protocol.md`](../docs/dataset_protocol.md) for the source layout,
protocol, and manifest contract.
