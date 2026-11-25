"""Row-level validation and quarantine.

Every incoming row is either a valid :class:`SaleRecord` or a
quarantined row carrying the reason it was rejected. Nothing is
silently dropped: the caller writes the quarantined rows to the
quarantine file and logs the counts from the returned report.
Duplicate ``transaction_id`` values keep the first occurrence and
quarantine later ones.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Iterable, Mapping

from .exceptions import ValidationError
from .models import DataQualityReport, SaleRecord

REQUIRED_COLUMNS: tuple[str, ...] = (
    "transaction_id",
    "dealer_id",
    "quarter",
    "units",
)


@dataclass(frozen=True)
class QuarantinedRow:
    """A rejected input row, kept for audit instead of being dropped."""

    row: dict[str, str]
    reason: str

    def to_dict(self) -> dict[str, str]:
        return {**self.row, "quarantine_reason": self.reason}


def validate_rows(
    rows: Iterable[Mapping[str, object]],
) -> tuple[list[SaleRecord], list[QuarantinedRow], DataQualityReport]:
    """Validate raw rows, quarantining bad and duplicate ones.

    Returns ``(valid_records, quarantined_rows, report)``. The report
    counts rows in, valid rows, rejected rows, duplicates, and rejected
    rows by reason, so a build can log exactly what happened to its
    input.
    """
    valid: list[SaleRecord] = []
    quarantined: list[QuarantinedRow] = []
    reasons: Counter[str] = Counter()
    seen_transaction_ids: set[str] = set()
    rows_in = 0
    duplicates = 0

    for raw in rows:
        rows_in += 1
        row = {key: ("" if value is None else str(value)) for key, value in raw.items()}
        try:
            record = SaleRecord.from_dict(raw)
        except ValidationError as exc:
            reason = str(exc)
            quarantined.append(QuarantinedRow(row=row, reason=reason))
            reasons[reason] += 1
            continue
        if record.transaction_id in seen_transaction_ids:
            duplicates += 1
            reason = f"duplicate transaction_id {record.transaction_id!r}"
            quarantined.append(QuarantinedRow(row=row, reason=reason))
            reasons[reason] += 1
            continue
        seen_transaction_ids.add(record.transaction_id)
        valid.append(record)

    report = DataQualityReport(
        rows_in=rows_in,
        rows_valid=len(valid),
        rows_rejected=len(quarantined),
        duplicates=duplicates,
        rejected_reasons=dict(reasons),
    )
    return valid, quarantined, report
