"""Typed data models with input validation.

``SaleRecord.from_dict`` is the single schema gate for incoming rows:
a row that fails it is quarantined by :mod:`validation`, never silently
coerced or dropped.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Mapping

from .exceptions import ValidationError

DEALER_ID_PATTERN = re.compile(r"^D\d{2}$")
QUARTER_PATTERN = re.compile(r"^\d{4}Q[1-4]$")
TRANSACTION_ID_PATTERN = re.compile(r"^D\d{2}-\d{4}Q[1-4]-T\d{2}$")


@dataclass(frozen=True)
class SaleRecord:
    """One validated synthetic dealer sale (one transaction)."""

    transaction_id: str
    dealer_id: str
    quarter: str
    units: int

    @classmethod
    def from_dict(cls, row: Mapping[str, object]) -> "SaleRecord":
        """Validate a raw mapping and return a SaleRecord.

        Raises ValidationError with a specific reason for a missing,
        empty, malformed, or out-of-range field. ``units`` must be an
        integer (or an integer string, as read from CSV); floats,
        non-numeric strings, and negative values are rejected.
        """
        transaction_id = _require_text(row, "transaction_id")
        dealer_id = _require_text(row, "dealer_id")
        quarter = _require_text(row, "quarter")
        units = _parse_units(row.get("units"))
        if not TRANSACTION_ID_PATTERN.match(transaction_id):
            raise ValidationError(
                f"transaction_id {transaction_id!r} does not match "
                "expected pattern D<nn>-<yyyy>Q<n>-T<nn>"
            )
        if not DEALER_ID_PATTERN.match(dealer_id):
            raise ValidationError(
                f"dealer_id {dealer_id!r} does not match expected pattern D<nn>"
            )
        if not QUARTER_PATTERN.match(quarter):
            raise ValidationError(
                f"quarter {quarter!r} does not match expected pattern <yyyy>Q<1-4>"
            )
        expected_prefix = f"{dealer_id}-{quarter}-"
        if not transaction_id.startswith(expected_prefix):
            raise ValidationError(
                f"transaction_id {transaction_id!r} does not belong to "
                f"dealer {dealer_id!r} and quarter {quarter!r}"
            )
        return cls(
            transaction_id=transaction_id,
            dealer_id=dealer_id,
            quarter=quarter,
            units=units,
        )


@dataclass(frozen=True)
class GoldRow:
    """One row of the gold table: a dealer, a quarter, its tier."""

    dealer_id: str
    quarter: str
    units: int
    bonus_tier: str
    variable_payment_estimate: int
    trend_flag: str
    prior_year_units: int | None

    def to_dict(self) -> dict[str, str]:
        """Serialise for CSV output (empty string when no prior year)."""
        return {
            "dealer_id": self.dealer_id,
            "quarter": self.quarter,
            "units": str(self.units),
            "bonus_tier": self.bonus_tier,
            "variable_payment_estimate": str(self.variable_payment_estimate),
            "trend_flag": self.trend_flag,
            "prior_year_units": (
                "" if self.prior_year_units is None else str(self.prior_year_units)
            ),
        }


@dataclass
class DataQualityReport:
    """Row counts for one build, for logging and for tests to assert on."""

    rows_in: int = 0
    rows_valid: int = 0
    rows_rejected: int = 0
    duplicates: int = 0
    gold_rows: int = 0
    rejected_reasons: dict[str, int] = field(default_factory=dict)

    def summary(self) -> str:
        return (
            f"rows_in={self.rows_in} rows_valid={self.rows_valid} "
            f"rows_rejected={self.rows_rejected} duplicates={self.duplicates} "
            f"gold_rows={self.gold_rows}"
        )


def _require_text(row: Mapping[str, object], name: str) -> str:
    value = row.get(name)
    if value is None or (isinstance(value, str) and not value.strip()):
        raise ValidationError(f"missing or empty {name}")
    if not isinstance(value, str):
        raise ValidationError(f"{name} must be text, got {type(value).__name__}")
    return value.strip()


def _parse_units(value: object) -> int:
    if value is None or (isinstance(value, str) and not value.strip()):
        raise ValidationError("missing or empty units")
    if isinstance(value, bool):
        raise ValidationError("units must be an integer, got a boolean")
    if isinstance(value, int):
        units = value
    elif isinstance(value, str):
        text = value.strip()
        try:
            units = int(text)
        except ValueError as exc:
            raise ValidationError(f"units {value!r} is not an integer") from exc
        if str(units) != text and text not in (f"+{units}",):
            # Rejects "12.0", "1_0", " 12 " handled by strip, etc.
            raise ValidationError(f"units {value!r} is not an integer")
    else:
        raise ValidationError(f"units must be an integer, got {type(value).__name__}")
    if units < 0:
        raise ValidationError(f"units must be >= 0, got {units}")
    return units
