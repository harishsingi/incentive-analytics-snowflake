"""Tests for the synthetic data generator."""

from incentive_analytics.config import Settings
from incentive_analytics.generate_data import generate_sales, main


def test_generate_is_deterministic_for_a_seed():
    settings = Settings(dealer_count=2, quarters=("2024Q1", "2024Q2"))
    first = generate_sales(settings)
    second = generate_sales(settings)
    assert first == second
    assert generate_sales(settings, seed=99) != first


def test_generate_covers_every_dealer_and_quarter():
    settings = Settings(dealer_count=3, quarters=("2024Q1", "2024Q2"))
    records = generate_sales(settings)
    keys = {(r.dealer_id, r.quarter) for r in records}
    assert keys == {
        (f"D{d:02d}", q) for d in (1, 2, 3) for q in ("2024Q1", "2024Q2")
    }
    assert all(40 <= r.units <= 180 for r in records)
    assert len({r.transaction_id for r in records}) == len(records)


def test_generate_quarterly_totals_span_tiers():
    # The old generator emitted one 40-220 row per dealer-quarter, so no
    # quarter could ever reach Gold (250) or Platinum (500). Several
    # transactions per quarter must make all three tiers reachable.
    settings = Settings()
    records = generate_sales(settings)
    totals: dict[tuple[str, str], int] = {}
    for record in records:
        key = (record.dealer_id, record.quarter)
        totals[key] = totals.get(key, 0) + record.units
    from incentive_analytics.tiers import tier_for_units

    tiers = {tier_for_units(total) for total in totals.values()}
    assert tiers == {"Standard", "Gold", "Platinum"}


def test_generate_main_writes_csv(tmp_path):
    output = tmp_path / "sales.csv"
    assert main(["--output", str(output), "--dealers", "2", "--seed", "5"]) == 0
    lines = output.read_text(encoding="utf-8").strip().splitlines()
    assert lines[0] == "transaction_id,dealer_id,quarter,units"
    assert len(lines) > 1
