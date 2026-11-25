"""Tests for validation / quarantine behaviour."""

from incentive_analytics.validation import validate_rows


def _row(tx="D01-2024Q1-T01", dealer="D01", quarter="2024Q1", units="120"):
    return {
        "transaction_id": tx,
        "dealer_id": dealer,
        "quarter": quarter,
        "units": units,
    }


def test_valid_rows_pass_and_bad_rows_quarantine_with_reasons():
    valid, quarantined, report = validate_rows(
        [
            _row(),
            _row(tx="D01-2024Q1-T02", units=""),
            _row(tx="D01-2024Q1-T03", units="-5"),
            _row(tx="D01-2024Q1-T04", quarter="2024Q9"),
        ]
    )
    assert len(valid) == 1
    assert len(quarantined) == 3
    assert report.rows_in == 4
    assert report.rows_valid == 1
    assert report.rows_rejected == 3
    assert report.duplicates == 0
    assert all("quarantine_reason" in q.to_dict() for q in quarantined)
    assert any("units" in q.reason for q in quarantined)


def test_duplicate_transaction_id_keeps_first_only():
    valid, quarantined, report = validate_rows([_row(), _row(), _row(tx="D01-2024Q1-T02")])
    assert [r.transaction_id for r in valid] == ["D01-2024Q1-T01", "D01-2024Q1-T02"]
    assert report.duplicates == 1
    assert report.rows_rejected == 1
    assert "duplicate" in quarantined[0].reason


def test_empty_input_reports_zeroes():
    valid, quarantined, report = validate_rows([])
    assert valid == [] and quarantined == []
    assert report.rows_in == 0 and report.rows_valid == 0
