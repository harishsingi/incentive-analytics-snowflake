"""CSV reading and writing.

All file access for the pipeline lives here so the transform modules
never touch paths directly. Paths come from settings (or CLI flags),
never from hardcoded strings inside the transforms.
"""

from __future__ import annotations

import csv
import logging
from pathlib import Path
from typing import Sequence

from .exceptions import DataQualityError
from .models import GoldRow
from .validation import REQUIRED_COLUMNS, QuarantinedRow

logger = logging.getLogger(__name__)

GOLD_COLUMNS: tuple[str, ...] = (
    "dealer_id",
    "quarter",
    "units",
    "bonus_tier",
    "variable_payment_estimate",
    "trend_flag",
    "prior_year_units",
)


def read_sales_csv(path: str | Path) -> list[dict[str, str]]:
    """Read raw sales rows from CSV.

    Raises DataQualityError if the file is missing, empty, or lacks a
    required column. Individual bad rows are returned as-is and left
    for :mod:`validation` to quarantine.
    """
    csv_path = Path(path)
    if not csv_path.exists():
        raise DataQualityError(f"sales file not found: {csv_path}")
    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise DataQualityError(f"sales file is empty: {csv_path}")
        missing = [col for col in REQUIRED_COLUMNS if col not in reader.fieldnames]
        if missing:
            raise DataQualityError(
                f"sales file {csv_path} is missing required column(s): "
                + ", ".join(missing)
            )
        rows = [
            {key: ("" if value is None else value) for key, value in row.items()}
            for row in reader
        ]
    if not rows:
        raise DataQualityError(f"sales file has no data rows: {csv_path}")
    logger.info("read %d raw rows from %s", len(rows), csv_path)
    return rows


def write_gold_csv(path: str | Path, rows: Sequence[GoldRow]) -> Path:
    """Write gold rows deterministically (input order) to CSV."""
    csv_path = Path(path)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(GOLD_COLUMNS))
        writer.writeheader()
        for row in rows:
            writer.writerow(row.to_dict())
    logger.info("wrote %d gold rows to %s", len(rows), csv_path)
    return csv_path


def write_quarantine_csv(path: str | Path, rows: Sequence[QuarantinedRow]) -> Path:
    """Write quarantined rows (with reasons) to CSV; header only if none."""
    csv_path = Path(path)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [*REQUIRED_COLUMNS, "quarantine_reason"]
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row.to_dict())
    logger.info("wrote %d quarantined rows to %s", len(rows), csv_path)
    return csv_path


def write_sales_csv(path: str | Path, rows: Sequence[dict[str, str]]) -> Path:
    """Write generated synthetic sales rows to CSV."""
    csv_path = Path(path)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(REQUIRED_COLUMNS))
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    logger.info("wrote %d sales rows to %s", len(rows), csv_path)
    return csv_path
