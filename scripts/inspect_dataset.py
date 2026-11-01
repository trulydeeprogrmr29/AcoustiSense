"""Inspect extracted DCASE Task 2 data or inventory ZIP archives without extraction."""

from __future__ import annotations

import argparse
import csv
import re
import sys
import zipfile
from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

MANIFEST_COLUMNS = (
    "file_path",
    "filename",
    "machine_type",
    "section",
    "domain",
    "partition",
    "condition",
    "recording_index",
    "metadata_source",
)

_MACHINE_ALIASES = {
    "fan": "fan",
    "gearbox": "gearbox",
    "pump": "pump",
    "slide rail": "slider",
    "slide_rail": "slider",
    "slide-rail": "slider",
    "slider": "slider",
    "toycar": "toycar",
    "toytrain": "toytrain",
    "valve": "valve",
}
_PARTITIONS = {"train", "source_test", "target_test"}
_FILENAME_PATTERN = re.compile(
    r"^section_(?P<section>\d+)_"
    r"(?:(?P<train_domain>source|target)_train_"
    r"(?P<train_condition>normal|anomaly)|"
    r"(?P<test_domain>source|target)_test"
    r"(?:_(?P<test_condition>normal|anomaly))?)_"
    r"(?P<recording_index>\d+)(?:_.*)?\.wav$",
    re.IGNORECASE,
)
_SECTION_PATTERN = re.compile(r"^section_(\d+)$", re.IGNORECASE)
_REQUIRED_METADATA = (
    "machine_type",
    "section",
    "domain",
    "partition",
    "condition",
    "recording_index",
)


@dataclass(frozen=True)
class ParsedFilename:
    """Metadata encoded in a recognized DCASE Task 2 WAV filename."""

    section: str
    domain: str
    partition: str
    condition: str
    recording_index: str


@dataclass(frozen=True)
class DatasetRecord:
    """One WAV inventory row using the shared training-manifest contract."""

    file_path: str
    filename: str
    machine_type: str = ""
    section: str = ""
    domain: str = "unknown"
    partition: str = ""
    condition: str = "unknown"
    recording_index: str = ""
    metadata_source: str = "unknown"
    unexpected_filename: bool = False
    metadata_warnings: tuple[str, ...] = ()

    @property
    def missing_metadata(self) -> tuple[str, ...]:
        """Return metadata fields that could not be determined."""
        values = {
            "machine_type": self.machine_type,
            "section": self.section,
            "domain": "" if self.domain == "unknown" else self.domain,
            "partition": self.partition,
            "condition": "" if self.condition == "unknown" else self.condition,
            "recording_index": self.recording_index,
        }
        return tuple(name for name in _REQUIRED_METADATA if not values[name])

    def manifest_row(self) -> dict[str, str]:
        """Return only the nine agreed manifest columns."""
        return {column: getattr(self, column) for column in MANIFEST_COLUMNS}


@dataclass(frozen=True)
class DirectoryInspection:
    """Inventory and structural warnings for an extracted dataset directory."""

    root: Path
    records: tuple[DatasetRecord, ...]
    missing_directories: tuple[str, ...]


@dataclass(frozen=True)
class ArchiveInspection:
    """Inventory of WAV members in a ZIP file, or an explicit archive error."""

    archive_path: Path
    records: tuple[DatasetRecord, ...] = ()
    error: str | None = None


def parse_filename(filename: str) -> ParsedFilename | None:
    """Parse standard DCASE Task 2 development or unlabeled evaluation filenames."""
    match = _FILENAME_PATTERN.fullmatch(filename)
    if match is None:
        return None

    train_domain = match.group("train_domain")
    test_domain = match.group("test_domain")
    domain = (train_domain or test_domain).lower()
    partition = "train" if train_domain else f"{test_domain.lower()}_test"
    condition = match.group("train_condition") or match.group("test_condition") or "unknown"

    return ParsedFilename(
        section=match.group("section"),
        domain=domain,
        partition=partition,
        condition=condition.lower(),
        recording_index=match.group("recording_index"),
    )


def record_from_path(file_path: str | Path | PurePosixPath) -> DatasetRecord:
    """Build manifest metadata from a root-relative path or ZIP member name."""
    if isinstance(file_path, Path):
        relative_path = file_path.as_posix()
    else:
        relative_path = str(file_path).replace("\\", "/")

    path = PurePosixPath(relative_path)
    filename = path.name
    directory_parts = path.parts[:-1]
    parsed = parse_filename(filename)
    warnings: list[str] = []
    directory_values: dict[str, str] = {}

    machine_matches = [
        _MACHINE_ALIASES[part.casefold()]
        for part in directory_parts
        if part.casefold() in _MACHINE_ALIASES
    ]
    if machine_matches:
        directory_values["machine_type"] = machine_matches[-1]
        if len(set(machine_matches)) > 1:
            warnings.append("conflicting machine type directories")

    for part in directory_parts:
        normalized = part.casefold()
        if normalized in _PARTITIONS:
            directory_values["partition"] = normalized
            if normalized == "source_test":
                directory_values["domain"] = "source"
            elif normalized == "target_test":
                directory_values["domain"] = "target"

        section_match = _SECTION_PATTERN.fullmatch(part)
        if section_match:
            directory_values["section"] = section_match.group(1)
        if normalized in {"normal", "anomaly"}:
            directory_values["condition"] = normalized

    filename_values: dict[str, str] = {}
    if parsed is not None:
        filename_values = {
            "section": parsed.section,
            "domain": parsed.domain,
            "partition": parsed.partition,
            "condition": parsed.condition,
            "recording_index": parsed.recording_index,
        }

    values = {**directory_values, **filename_values}
    for field in ("machine_type", "section", "domain", "partition", "condition"):
        directory_value = directory_values.get(field)
        filename_value = filename_values.get(field)
        if directory_value and filename_value and directory_value != filename_value:
            warnings.append(
                f"{field} conflict: directory says {directory_value}, "
                f"filename says {filename_value}"
            )

    directory_has_metadata = bool(directory_values)
    filename_has_metadata = bool(filename_values)
    if directory_has_metadata and filename_has_metadata:
        metadata_source = "both"
    elif filename_has_metadata:
        metadata_source = "filename"
    elif directory_has_metadata:
        metadata_source = "directory"
    else:
        metadata_source = "unknown"

    return DatasetRecord(
        file_path=path.as_posix(),
        filename=filename,
        machine_type=values.get("machine_type", ""),
        section=values.get("section", ""),
        domain=values.get("domain", "unknown"),
        partition=values.get("partition", ""),
        condition=values.get("condition", "unknown"),
        recording_index=values.get("recording_index", ""),
        metadata_source=metadata_source,
        unexpected_filename=parsed is None,
        metadata_warnings=tuple(warnings),
    )


def _expected_dataset_location(root: Path) -> tuple[Path, tuple[str, ...]]:
    """Resolve the directory that should contain machine folders."""
    normalized_root_name = _MACHINE_ALIASES.get(root.name.casefold())
    if normalized_root_name:
        return root.parent, (normalized_root_name,)
    if (root / "dev_data").is_dir():
        return root / "dev_data", ("fan", "pump")
    if root.name.casefold() == "dev_data":
        return root, ("fan", "pump")
    return root, ("fan", "pump")


def inspect_directory(root: Path) -> DirectoryInspection:
    """Recursively inventory WAV files and check expected fan/pump directories."""
    root = root.expanduser().resolve()
    if not root.is_dir():
        raise NotADirectoryError(f"Dataset root is not a directory: {root}")

    wav_paths = sorted(
        (path for path in root.rglob("*") if path.is_file() and path.suffix.casefold() == ".wav"),
        key=lambda path: path.as_posix().casefold(),
    )
    records = tuple(record_from_path(path.relative_to(root)) for path in wav_paths)

    dataset_location, expected_machines = _expected_dataset_location(root)
    missing_directories = tuple(
        (dataset_location / machine / partition).as_posix()
        for machine in expected_machines
        for partition in sorted(_PARTITIONS)
        if not (dataset_location / machine / partition).is_dir()
    )
    return DirectoryInspection(root, records, missing_directories)


def inspect_archive(archive_path: Path) -> ArchiveInspection:
    """Inventory WAV ZIP members without reading or extracting their contents."""
    archive_path = archive_path.expanduser().resolve()
    try:
        with zipfile.ZipFile(archive_path) as archive:
            records = tuple(
                record_from_path(member.filename)
                for member in archive.infolist()
                if (
                    not member.is_dir()
                    and PurePosixPath(member.filename).suffix.casefold() == ".wav"
                )
            )
    except (OSError, zipfile.BadZipFile, zipfile.LargeZipFile) as exc:
        return ArchiveInspection(archive_path=archive_path, error=str(exc))

    return ArchiveInspection(archive_path=archive_path, records=records)


def export_manifest(records: Iterable[DatasetRecord], output_path: Path) -> Path:
    """Write extracted-directory records with exactly the shared nine columns."""
    output_path = output_path.expanduser()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as manifest_file:
        writer = csv.DictWriter(manifest_file, fieldnames=MANIFEST_COLUMNS)
        writer.writeheader()
        writer.writerows(record.manifest_row() for record in records)
    return output_path.resolve()


def _counts(records: Sequence[DatasetRecord], field: str) -> Counter[str]:
    return Counter(getattr(record, field) or "unknown" for record in records)


def _print_counts(label: str, counts: Counter[str]) -> None:
    print(f"{label}:")
    if not counts:
        print("  (none)")
        return
    for key, count in sorted(counts.items()):
        print(f"  {key}: {count}")


def _print_summary(
    label: str,
    records: Sequence[DatasetRecord],
    missing_directories: Sequence[str] = (),
    manifest_path: Path | None = None,
) -> None:
    print(f"\n{label}")
    print(f"Total WAV files: {len(records)}")
    if not records:
        print("No WAV files were found.")

    for field, title in (
        ("machine_type", "Machine-wise counts"),
        ("section", "Section-wise counts"),
        ("domain", "Domain-wise counts"),
        ("partition", "Partition-wise counts"),
        ("condition", "Condition-wise counts"),
    ):
        _print_counts(title, _counts(records, field))

    grouped = Counter(
        (
            record.machine_type or "unknown",
            record.section or "unknown",
            record.domain,
            record.partition or "unknown",
            record.condition,
        )
        for record in records
    )
    print("Machine/section/domain/partition/condition counts:")
    if grouped:
        for group, count in sorted(grouped.items()):
            print(f"  {' / '.join(group)}: {count}")
    else:
        print("  (none)")

    unexpected = [record.file_path for record in records if record.unexpected_filename]
    print(f"Unexpected filenames: {len(unexpected)}")
    for file_path in unexpected[:20]:
        print(f"  {file_path}")
    if len(unexpected) > 20:
        print(f"  ... {len(unexpected) - 20} more")

    incomplete = [record for record in records if record.missing_metadata]
    inconsistent = [record for record in records if record.metadata_warnings]
    print(f"Incomplete metadata: {len(incomplete)}")
    for record in incomplete[:20]:
        missing = ", ".join(record.missing_metadata)
        print(f"  {record.file_path}: missing {missing}")
    if len(incomplete) > 20:
        print(f"  ... {len(incomplete) - 20} more")

    print(f"Inconsistent metadata: {len(inconsistent)}")
    for record in inconsistent[:20]:
        print(f"  {record.file_path}: {'; '.join(record.metadata_warnings)}")
    if len(inconsistent) > 20:
        print(f"  ... {len(inconsistent) - 20} more")

    print(f"Missing expected directories: {len(missing_directories)}")
    for directory in missing_directories:
        print(f"  {directory}")

    if manifest_path is not None:
        print(f"Manifest: {manifest_path}")


def _argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Inspect extracted DCASE Task 2 data or list WAV members in ZIP archives."
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--root", type=Path, help="extracted dataset root directory")
    source.add_argument(
        "--archive",
        nargs="+",
        type=Path,
        help="one or more ZIP archives to inventory without extraction",
    )
    parser.add_argument(
        "--export-manifest",
        type=Path,
        help="CSV output path; accepted only with --root",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run dataset directory or ZIP inventory from the command line."""
    parser = _argument_parser()
    args = parser.parse_args(argv)
    if args.export_manifest is not None and args.root is None:
        parser.error("--export-manifest is available only with --root.")

    if args.root is not None:
        try:
            inspection = inspect_directory(args.root)
            manifest_path = (
                export_manifest(inspection.records, args.export_manifest)
                if args.export_manifest is not None
                else None
            )
        except OSError as exc:
            print(f"Dataset inspection error: {exc}", file=sys.stderr)
            return 1

        _print_summary(
            f"Dataset root: {inspection.root}",
            inspection.records,
            inspection.missing_directories,
            manifest_path,
        )
        return 0

    exit_code = 0
    for archive_path in args.archive:
        inspection = inspect_archive(archive_path)
        if inspection.error is not None:
            print(f"\nArchive: {inspection.archive_path}")
            print(f"Archive error: {inspection.error}", file=sys.stderr)
            exit_code = 1
            continue
        _print_summary(f"ZIP archive: {inspection.archive_path}", inspection.records)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
