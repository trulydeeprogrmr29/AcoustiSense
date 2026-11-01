# DCASE 2021 Task 2 dataset protocol

## Research objective

Investigate unsupervised acoustic anomaly detection for industrial machines,
including robustness to domain shift. The initial local scope is fans and
pumps from development sections 00, 01, and 02. This is not a remaining-useful-
life or exact-failure-time prediction task.

## Dataset selection and relationship

The primary source is the [DCASE 2021 Challenge Task 2 Development
Dataset](https://zenodo.org/records/4562016), DOI
[10.5281/zenodo.4562016](https://doi.org/10.5281/zenodo.4562016). It contains
seven machine categories: fan, gearbox, pump, slide rail (`slider`), ToyCar,
ToyTrain, and valve.

[MIMII DUE](https://zenodo.org/records/4740355) is explicitly documented as a
subset of DCASE 2021 Task 2 data. Its record states that its data is the same
as data included in the DCASE development and additional-training datasets.
Consequently, do not treat MIMII DUE as an independent sample or download both
releases for the same experiment. The MIMII DUE paper describes the domain
shift motivation and subset:
[Tanabe et al., 2021](https://arxiv.org/abs/2105.02702).

The [original MIMII dataset](https://zenodo.org/records/3384388) is an earlier
and separate dataset release. It is not the selected primary data for this
phase.

## Official sources

- [DCASE 2021 Task 2 description and protocol](https://dcase.community/challenge2021/task-unsupervised-detection-of-anomalous-sounds)
- [DCASE 2021 development dataset and downloads](https://zenodo.org/records/4562016)
- [Official autoencoder baseline repository and data layout](https://github.com/y-kawagu/dcase2021_task2_baseline_ae)
- [DCASE 2021 additional-training dataset, sections 03-05](https://zenodo.org/records/4660992)
- [MIMII DUE record](https://zenodo.org/records/4740355)
- [MIMII DUE paper](https://arxiv.org/abs/2105.02702)
- [Original MIMII record](https://zenodo.org/records/3384388)

The development record provides machine-specific ZIP archives such as
`dev_data_fan.zip` and `dev_data_pump.zip`. This project does not download or
extract them automatically.

## Relevant categories and directory structure

The DCASE development dataset uses sections 00, 01, and 02 for each machine
category. In the extracted tree, the machine type is conveyed by the directory
name, and the development partitions are:

```text
dev_data/
  fan/
    train/
    source_test/
    target_test/
  pump/
    train/
    source_test/
    target_test/
```

Other machine categories follow the same layout. ZIP contents and local
archives should be inspected rather than assumed to have this exact prefix.

## Filename and metadata interpretation

Development filenames follow these forms:

```text
section_<section>_<domain>_train_normal_<index>_<attribute>.wav
section_<section>_<domain>_test_<condition>_<index>.wav
```

`<domain>` is `source` or `target`; `<condition>` is `normal` or `anomaly`.
Training recordings are normal and may include a trailing attribute string
after the numeric index. The test directory determines whether the test
partition is `source_test` or `target_test`; the filename also identifies its
domain. A filename such as `section_03_source_test_0199.wav` is an
unlabelled evaluation example, not a development-labelled normal/anomaly file.

Metadata sources:

- Machine type: machine directory name.
- Section: filename.
- Domain: filename; for test recordings it is also represented by the test
  directory.
- Partition: training/test directory and filename.
- Condition: development filename; training is normal. Some later evaluation
  files intentionally do not disclose the condition.
- Training attributes: trailing filename text; retained in the original
  filename but not parsed into the shared manifest.

The inspector reports missing metadata as blank fields or the contract's
`unknown` value and reports filename/directory conflicts. It does not invent
labels for malformed or unlabelled files.

## Source/target domains and split protocol

The source domain contains most training recordings. The target domain
represents a changed operating or environmental condition and has only a few
normal training examples. The intended development protocol has, **per machine
section**, approximately:

- 1,000 normal source-domain training clips;
- 3 normal target-domain training clips;
- around 100 normal and 100 anomalous source-domain test clips; and
- around 100 normal and 100 anomalous target-domain test clips.

These are official approximate counts, not assertions enforced by the
inspector. Report counts observed in the acquired release. Keep `source_test`
and `target_test` groups distinct in all inventories and later evaluation.
The development set covers sections 00-02; the additional-training dataset
covers sections 03-05 and is outside this initial scope.

## Leakage prevention and evaluation

- Follow the official section/domain partitions; never move test clips into
  training or validation.
- Do not use test labels or scores to select preprocessing, model parameters,
  or anomaly thresholds.
- Calibrate any threshold using a designated validation set drawn only from
  permitted training data, and document that selection.
- Preserve machine, section, domain, and partition identifiers in manifests
  and metrics; do not aggregate away source/target differences.
- Dataset counts and metadata inspection are not model performance results.

## Manifest contract

For extracted directory trees only, the inspector writes a CSV with exactly
these columns in this order:

1. `file_path` — path relative to the extracted dataset root, with `/`
   separators.
2. `filename` — original WAV filename.
3. `machine_type`
4. `section`
5. `domain` — `source`, `target`, or `unknown`.
6. `partition` — `train`, `source_test`, `target_test`, or blank when unknown.
7. `condition` — `normal`, `anomaly`, or `unknown`.
8. `recording_index` — numeric filename index when recognized.
9. `metadata_source` — `filename`, `directory`, `both`, or `unknown`.

ZIP inventory does not export a manifest because a member path does not prove
the referenced file exists as an extracted file.

## Licensing and attribution

The DCASE 2021 development dataset Zenodo record specifies
[Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International
(CC BY-NC-SA 4.0)](https://creativecommons.org/licenses/by-nc-sa/4.0/).
The MIMII DUE record specifies the same license. The separate original MIMII
record specifies [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/).
Check the terms on the exact record/version you use; do not assume these
dataset licenses apply to project code or other data.

When using DCASE 2021 Task 2 data, cite the challenge description paper and
follow attribution and non-commercial/share-alike requirements:

> Yohei Kawaguchi, Keisuke Imoto, Yuma Koizumi, Noboru Harada, Daisuke
> Niizumi, Kota Dohi, Ryo Tanabe, Harsh Purohit, and Takashi Endo,
> “Description and Discussion on DCASE 2021 Challenge Task 2: Unsupervised
> Anomalous Sound Detection for Machine Condition Monitoring under Domain
> Shifted Conditions,” arXiv:2106.04492, 2021.

The MIMII DUE record requests citation of:

> Ryo Tanabe, Harsh Purohit, Kota Dohi, Takashi Endo, Yuki Nikaido, Toshiki
> Nakamura, and Yohei Kawaguchi, “MIMII DUE: Sound Dataset for Malfunctioning
> Industrial Machine Investigation and Inspection with Domain Shifts due to
> Changes in Operational and Environmental Conditions,” arXiv:2105.02702, 2021.

For the separate original MIMII release, its record cites:

> Harsh Purohit, Ryo Tanabe, Kenji Ichige, Takashi Endo, Yuki Nikaido, Kaori
> Suefusa, and Yohei Kawaguchi, “MIMII Dataset: Sound Dataset for
> Malfunctioning Industrial Machine Investigation and Inspection,” arXiv
> preprint arXiv:1909.09347, 2019.

## Future dataset expansion

Any expansion to DCASE sections 03-05, MIMII DUE mirrors, the earlier MIMII
release, or additional machine classes requires explicit source/version
tracking and a reviewed split protocol. Do not combine duplicate releases or
claim independent evaluation across overlapping data.
