"""Tests for SaleRecord / GoldRow validation."""

import pytest

from incentive_analytics.exceptions import ValidationError
from incentive_analytics.models import GoldRow, SaleRecord


def _row(**overrides):
    row = {
        "transaction_id": "D01-2024Q1-T01",
        "dealer_id": "D01",
        "quarter": "2024Q1",
        "units": "120",
    }
    row.update(overrides)
    return row


def test_valid_row_parses():
    record = SaleRecord.from_dict(_row())
    assert record == SaleRecord("D01-2024Q1-T01", "D01", "2024Q1", 120)


def test_valid_row_accepts_int_units():
    assert SaleRecord.from_dict(_row(units=120)).units == 120


@pytest.mark.parametrize(
    "overrides",
    [
        {"dealer_id": ""},
        {"dealer_id": "Dealer1"},
        {"quarter": "2024Q5"},
        {"quarter": "24Q1"},
        {"units": ""},
        {"units": "12.5"},
        {"units": "-3"},
        {"units": "abc"},
        {"transaction_id": "D02-2024Q1-T01"},  # wrong dealer for D01
        {"transaction_id": "not-an-id"},
    ],
)
def test_invalid_rows_rejected(overrides):
    with pytest.raises(ValidationError):
        SaleRecord.from_dict(_row(**overrides))


def test_missing_field_rejected():
    row = _row()
    del row["units"]
    with pytest.raises(ValidationError):
        SaleRecord.from_dict(row)


def test_gold_row_serialises_empty_prior_year():
    row = GoldRow("D01", "2024Q1", 120, "Standard", 6000, "no_baseline", None)
    assert row.to_dict()["prior_year_units"] == ""
    assert row.to_dict()["variable_payment_estimate"] == "6000"
