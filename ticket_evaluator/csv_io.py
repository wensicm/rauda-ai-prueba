"""CSV input/output helpers."""

import csv
from pathlib import Path
from typing import Iterable

BASE_OUTPUT_FIELDS = [
    "ticket",
    "reply",
    "content_score",
    "content_explanation",
    "format_score",
    "format_explanation",
]
METADATA_OUTPUT_FIELDS = [
    "evaluation_status",
    "evaluation_error",
]


def read_rows(path: Path) -> list[dict]:
    if not path.exists():
        raise FileNotFoundError(f"Input file does not exist: {path}")

    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames:
            reader.fieldnames = [name.strip().lstrip("\ufeff") for name in reader.fieldnames]
        rows = list(reader)

    required = {"ticket", "reply"}
    if rows:
        missing = required.difference(rows[0].keys())
        if missing:
            raise ValueError(f"Missing required columns: {', '.join(sorted(missing))}")
    elif not rows:
        raise ValueError("Input CSV has no rows")

    return rows


def write_rows(path: Path, rows: Iterable[dict], include_metadata: bool = False) -> None:
    output_rows = list(rows)
    fieldnames = list(BASE_OUTPUT_FIELDS)
    if include_metadata:
        fieldnames.extend(METADATA_OUTPUT_FIELDS)

    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(output_rows)
