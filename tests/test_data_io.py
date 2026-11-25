"""Tests for CSV reading/writing."""

import pytest

from incentive_analytics.data_io import (
    read_sales_csv,
    write_gold_csv,
    write_quarantine_csv,
)
from incentive_analytics.exceptions import DataQualityError
from incentive_analytics.models import GoldRow
from incentive_analytics.validation import QuarantinedRow


def test_read_sales_csv(tmp_path):
    path = tmp_path / "sales.csv"
    path.write_text(
        "transaction_id,dealer_id,quarter,units\n"
        "D01-2024Q1-T01,D01,2024Q1,120\n",
        encoding="utf-8",
    )
    rows = read_sales_csv(path)
    assert rows == [
        {
            "transaction_id": "D01-2024Q1-T01",
            "dealer_id": "D01",
            "quarter": "2024Q1",
            "units": "120",
        }
    ]


def test_read_sales_csv_missing_file(tmp_path):
    with pytest.raises(DataQualityError):
        read_sales_csv(tmp_path / "nope.csv")


def test_read_sales_csv_missing_column(tmp_path):
    path = tmp_path / "sales.csv"
    path.write_text("dealer_id,quarter,units\nD01,2024Q1,120\n", encoding="utf-8")
    with pytest.raises(DataQualityError, match="transaction_id"):
        read_sales_csv(path)


def test_read_sales_csv_empty_file(tmp_path):
    path = tmp_path / "sales.csv"
    path.write_text("", encoding="utf-8")
    with pytest.raises(DataQualityError):
        read_sales_csv(path)


def test_write_gold_and_quarantine_round_trip(tmp_path):
    gold_path = tmp_path / "nested" / "gold.csv"
    write_gold_csv(
        gold_path,
        [GoldRow("D01", "2024Q1", 120, "Standard", 6000, "no_baseline", None)],
    )
    assert "D01,2024Q1,120,Standard,6000,no_baseline," in gold_path.read_text(
        encoding="utf-8"
    )
    quarantine_path = tmp_path / "quarantine.csv"
    write_quarantine_csv(
        quarantine_path,
        [
            QuarantinedRow(
                row={
                    "transaction_id": "D01-2024Q1-T01",
                    "dealer_id": "D01",
                    "quarter": "2024Q1",
                    "units": "",
                },
                reason="missing or empty units",
            )
        ],
    )
    assert "missing or empty units" in quarantine_path.read_text(encoding="utf-8")
