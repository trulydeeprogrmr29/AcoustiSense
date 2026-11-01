"""Tests for the standard-library DCASE dataset inspection utility."""

from __future__ import annotations

import csv
import zipfile
from collections import Counter
from pathlib import Path

import pytest

from scripts.inspect_dataset import (
    MANIFEST_COLUMNS,
    export_manifest,
    inspect_archive,
    inspect_directory,
    parse_filename,
    record_from_path,
)


@pytest.mark.parametrize(
    ("filename", "expected"),
    [
        (
            "section_00_source_train_normal_0000_attribute.wav",
            ("00", "source", "train", "normal", "0000"),
        ),
        (
            "section_01_target_train_normal_0002_attribute.wav",
            ("01", "target", "train", "normal", "0002"),
        ),
        (
            "section_00_source_test_normal_0001.wav",
            ("00", "source", "source_test", "normal", "0001"),
        ),
        (
            "section_02_source_test_anomaly_0099.wav",
            ("02", "source", "source_test", "anomaly", "0099"),
        ),
        (
            "section_01_target_test_normal_0012.wav",
            ("01", "target", "target_test", "normal", "0012"),
        ),
        (
            "section_02_target_test_anomaly_0087.wav",
            ("02", "target", "target_test", "anomaly", "0087"),
        ),
    ],
)
def test_parse_valid_filename(filename: str, expected: tuple[str, ...]) -> None:
    parsed = parse_filename(filename)

    assert parsed is not None
    assert (
        parsed.section,
        parsed.domain,
        parsed.partition,
        parsed.condition,
        parsed.recording_index,
    ) == expected


def test_parse_unlabeled_evaluation_test_filename() -> None:
    parsed = parse_filename("section_03_source_test_0199.wav")

    assert parsed is not None
    assert parsed.condition == "unknown"
    assert parsed.domain == "source"
    assert parsed.partition == "source_test"
    assert parsed.recording_index == "0199"


def test_invalid_filename_is_not_guessed() -> None:
    assert parse_filename("unrecognized.wav") is None

    record = record_from_path("other/fan/train/unrecognized.wav")
    assert record.unexpected_filename
    assert record.machine_type == "fan"
    assert record.partition == "train"
    assert record.domain == "unknown"
    assert record.condition == "unknown"
    assert record.metadata_source == "directory"


def test_unknown_path_has_unknown_metadata() -> None:
    record = record_from_path("unclassified/unrecognized.wav")

    assert record.machine_type == ""
    assert record.section == ""
    assert record.domain == "unknown"
    assert record.partition == ""
    assert record.condition == "unknown"
    assert record.recording_index == ""
    assert record.metadata_source == "unknown"


def test_path_metadata_and_filename_metadata_are_combined() -> None:
    record = record_from_path(
        "dev_data/fan/train/section_00_target_train_normal_0002_noise.wav"
    )

    assert record.machine_type == "fan"
    assert record.section == "00"
    assert record.domain == "target"
    assert record.partition == "train"
    assert record.condition == "normal"
    assert record.recording_index == "0002"
    assert record.metadata_source == "both"


def test_conflicting_directory_and_filename_metadata_is_reported() -> None:
    record = record_from_path("dev_data/fan/source_test/section_00_target_test_normal_0001.wav")

    assert record.domain == "target"
    assert any("domain conflict" in warning for warning in record.metadata_warnings)
    assert any("partition conflict" in warning for warning in record.metadata_warnings)


def test_directory_inspection_aggregates_metadata_and_exports_manifest(tmp_path: Path) -> None:
    root = tmp_path / "dcase"
    paths = (
        "dev_data/fan/train/section_00_source_train_normal_0000_attribute.wav",
        "dev_data/fan/train/section_00_target_train_normal_0000_attribute.wav",
        "dev_data/fan/source_test/section_00_source_test_anomaly_0000.wav",
        "dev_data/pump/target_test/section_01_target_test_normal_0001.wav",
    )
    for relative_path in paths:
        wav_path = root / Path(relative_path)
        wav_path.parent.mkdir(parents=True, exist_ok=True)
        wav_path.touch()

    inspection = inspect_directory(root)
    assert len(inspection.records) == 4
    assert Counter(record.machine_type for record in inspection.records) == {
        "fan": 3,
        "pump": 1,
    }
    assert Counter(record.domain for record in inspection.records) == {
        "source": 2,
        "target": 2,
    }
    assert Counter(record.partition for record in inspection.records) == {
        "train": 2,
        "source_test": 1,
        "target_test": 1,
    }
    assert len(inspection.missing_directories) == 3

    output_path = export_manifest(inspection.records, tmp_path / "manifests" / "data.csv")
    with output_path.open(newline="", encoding="utf-8") as manifest_file:
        reader = csv.DictReader(manifest_file)
        assert tuple(reader.fieldnames or ()) == MANIFEST_COLUMNS
        rows = list(reader)

    assert len(rows) == 4
    assert {row["machine_type"] for row in rows} == {"fan", "pump"}
    assert {row["domain"] for row in rows} == {"source", "target"}
    assert {row["partition"] for row in rows} == {"train", "source_test", "target_test"}
    assert rows[0]["file_path"].startswith("dev_data/")
    assert "\\" not in rows[0]["file_path"]
    assert all(set(row) == set(MANIFEST_COLUMNS) for row in rows)


def test_empty_directory_reports_no_wavs(tmp_path: Path) -> None:
    inspection = inspect_directory(tmp_path)

    assert inspection.records == ()
    assert len(inspection.missing_directories) == 6


def test_zip_inspection_counts_members_without_extracting(tmp_path: Path) -> None:
    archive_path = tmp_path / "dev_data_fan.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr(
            "dev_data/fan/train/section_00_source_train_normal_0000_attribute.wav",
            b"test fixture, not audio",
        )
        archive.writestr(
            "dev_data/fan/target_test/section_00_target_test_anomaly_0001.wav",
            b"test fixture, not audio",
        )
        archive.writestr("dev_data/fan/readme.txt", "not a WAV")

    inspection = inspect_archive(archive_path)

    assert inspection.error is None
    assert len(inspection.records) == 2
    assert not (tmp_path / "dev_data").exists()
    assert {record.machine_type for record in inspection.records} == {"fan"}
    assert {record.condition for record in inspection.records} == {"normal", "anomaly"}


def test_corrupt_zip_is_reported(tmp_path: Path) -> None:
    archive_path = tmp_path / "corrupt.zip"
    archive_path.write_bytes(b"not a zip file")

    inspection = inspect_archive(archive_path)

    assert inspection.records == ()
    assert inspection.error is not None
