"""Tests for the gold-table build, end to end."""

import csv

import pytest

from incentive_analytics.build_gold import (
    build_gold_rows,
    main,
    prior_year_quarter,
    run_build,
)
from incentive_analytics.config import Settings
from incentive_analytics.exceptions import DataQualityError, ValidationError
from incentive_analytics.models import SaleRecord


def _record(dealer, quarter, units, seq=1):
    return SaleRecord(f"{dealer}-{quarter}-T{seq:02d}", dealer, quarter, units)


def test_prior_year_quarter():
    assert prior_year_quarter("2025Q3") == "2024Q3"
    assert prior_year_quarter("2024Q1") == "2023Q1"
    with pytest.raises(ValidationError):
        prior_year_quarter("2024Q5")
    with pytest.raises(ValidationError):
        prior_year_quarter("not-a-quarter")


def test_build_gold_rows_tiers_payments_and_trends():
    records = [
        _record("D01", "2024Q1", 300),
        _record("D01", "2024Q1", 250, seq=2),  # 550 total -> Platinum
        _record("D01", "2025Q1", 600),  # +9% vs 550 -> improving
        _record("D02", "2024Q1", 100),  # Standard, no baseline
        _record("D02", "2025Q1", 90),  # -10% -> declining
        _record("D03", "2024Q1", 200),
        _record("D03", "2025Q1", 205),  # +2.5% -> flat
    ]
    rows = build_gold_rows(records)
    by_key = {(r.dealer_id, r.quarter): r for r in rows}
    assert len(rows) == 6
    assert [(r.dealer_id, r.quarter) for r in rows] == sorted(by_key)
    d01_2024 = by_key[("D01", "2024Q1")]
    assert d01_2024.units == 550
    assert d01_2024.bonus_tier == "Platinum"
    assert d01_2024.variable_payment_estimate == 550 * 150
    assert d01_2024.trend_flag == "no_baseline"
    assert d01_2024.prior_year_units is None
    assert by_key[("D01", "2025Q1")].trend_flag == "improving"
    assert by_key[("D02", "2025Q1")].trend_flag == "declining"
    assert by_key[("D03", "2025Q1")].trend_flag == "flat"


def test_run_build_end_to_end_quarantines_bad_rows_and_is_idempotent(tmp_path):
    sales = tmp_path / "sales.csv"
    sales.write_text(
        "transaction_id,dealer_id,quarter,units\n"
        "D01-2024Q1-T01,D01,2024Q1,300\n"
        "D01-2024Q1-T02,D01,2024Q1,250\n"
        "D01-2024Q1-T02,D01,2024Q1,250\n"  # duplicate transaction_id
        "D02-2024Q1-T01,D02,2024Q1,\n"  # missing units
        "D02-2024Q1-T02,D02,2024Q1,100\n",
        encoding="utf-8",
    )
    gold = tmp_path / "gold.csv"
    quarantine = tmp_path / "quarantine.csv"
    report = run_build(sales, gold, quarantine, Settings())
    assert report.rows_in == 5
    assert report.rows_valid == 3
    assert report.rows_rejected == 2
    assert report.duplicates == 1
    assert report.gold_rows == 2
    with gold.open(newline="", encoding="utf-8") as handle:
        gold_rows = list(csv.DictReader(handle))
    assert [r["dealer_id"] for r in gold_rows] == ["D01", "D02"]
    assert gold_rows[0]["bonus_tier"] == "Platinum"
    assert gold_rows[0]["variable_payment_estimate"] == str(550 * 150)
    assert gold_rows[0]["trend_flag"] == "no_baseline"
    with quarantine.open(newline="", encoding="utf-8") as handle:
        quarantined = list(csv.DictReader(handle))
    assert len(quarantined) == 2
    assert any("duplicate" in r["quarantine_reason"] for r in quarantined)

    first_bytes = gold.read_bytes()
    report_again = run_build(sales, gold, quarantine, Settings())
    assert gold.read_bytes() == first_bytes  # idempotent: same bytes
    assert report_again.gold_rows == 2


def test_run_build_missing_input_raises(tmp_path):
    with pytest.raises(DataQualityError):
        run_build(tmp_path / "missing.csv", tmp_path / "gold.csv",
                  tmp_path / "quarantine.csv", Settings())


def test_main_returns_nonzero_when_nothing_valid(tmp_path):
    sales = tmp_path / "sales.csv"
    sales.write_text(
        "transaction_id,dealer_id,quarter,units\n"
        "D01-2024Q1-T01,D01,2024Q1,\n",
        encoding="utf-8",
    )
    assert main(["--input", str(sales), "--output", str(tmp_path / "gold.csv"),
                 "--quarantine", str(tmp_path / "q.csv")]) == 1
