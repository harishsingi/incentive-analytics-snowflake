"""Build the gold table from validated sales data.

Pipeline: read CSV -> validate/quarantine -> aggregate per dealer per
quarter -> tier + variable-payment estimate + prior-year trend flag ->
write gold CSV and quarantine CSV.

The build is idempotent: the same input file always produces the same
gold file byte for byte (sorted output, full overwrite), so re-running
a build never duplicates rows.
"""

from __future__ import annotations

import argparse
import logging
from collections import Counter
from dataclasses import replace
from pathlib import Path

from .config import Settings, load_config
from .data_io import read_sales_csv, write_gold_csv, write_quarantine_csv
from .exceptions import ValidationError
from .logging_config import setup_logging
from .models import DataQualityReport, GoldRow, SaleRecord
from .tiers import tier_for_units, trend_flag, variable_payment_estimate
from .validation import validate_rows

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


def prior_year_quarter(quarter: str) -> str | None:
    """Return the same quarter last year, or None for the earliest year.

    Only the format is assumed here; a malformed quarter raises
    ValidationError rather than producing a wrong comparison.
    """
    if len(quarter) != 6 or quarter[4] != "Q" or quarter[5] not in "1234":
        raise ValidationError(f"invalid quarter: {quarter!r}")
    try:
        year = int(quarter[:4])
    except ValueError as exc:
        raise ValidationError(f"invalid quarter: {quarter!r}") from exc
    return f"{year - 1}Q{quarter[5]}"


def aggregate_sales(records: list[SaleRecord]) -> dict[tuple[str, str], int]:
    """Sum units per (dealer_id, quarter)."""
    totals: dict[tuple[str, str], int] = {}
    for record in records:
        key = (record.dealer_id, record.quarter)
        totals[key] = totals.get(key, 0) + record.units
    return totals


def build_gold_rows(
    records: list[SaleRecord], settings: Settings | None = None
) -> list[GoldRow]:
    """Aggregate validated records into sorted gold rows.

    Output is sorted by (dealer_id, quarter) so the build is
    deterministic. The trend flag compares each quarter with the same
    quarter last year when that quarter exists in the data.
    """
    cfg = settings or Settings()
    totals = aggregate_sales(records)
    rows: list[GoldRow] = []
    for (dealer_id, quarter), units in sorted(totals.items()):
        prior_quarter = prior_year_quarter(quarter)
        prior_units = totals.get((dealer_id, prior_quarter)) if prior_quarter else None
        tier = tier_for_units(units, cfg)
        rows.append(
            GoldRow(
                dealer_id=dealer_id,
                quarter=quarter,
                units=units,
                bonus_tier=tier,
                variable_payment_estimate=variable_payment_estimate(units, tier, cfg),
                trend_flag=trend_flag(
                    units, prior_units, cfg.trend_threshold_pct
                ),
                prior_year_units=prior_units,
            )
        )
    return rows


def run_build(
    input_path: str | Path,
    output_path: str | Path,
    quarantine_path: str | Path,
    settings: Settings | None = None,
) -> DataQualityReport:
    """Run one full build and return its data-quality report."""
    cfg = settings or Settings()
    raw_rows = read_sales_csv(input_path)
    valid, quarantined, report = validate_rows(raw_rows)
    gold_rows = build_gold_rows(valid, cfg)
    write_gold_csv(output_path, gold_rows)
    write_quarantine_csv(quarantine_path, quarantined)
    report = replace(report, gold_rows=len(gold_rows))
    tier_counts = Counter(row.bonus_tier for row in gold_rows)
    logger.info("build complete: %s; tiers: %s", report.summary(), dict(tier_counts))
    if quarantined:
        logger.warning(
            "%d row(s) quarantined; see %s", len(quarantined), quarantine_path
        )
    return report


def main(argv: list[str] | None = None) -> int:
    """CLI entry point: ``python -m incentive_analytics build-gold``."""
    parser = argparse.ArgumentParser(description="Build the gold bonus table.")
    parser.add_argument("--config", type=Path, default=None, help="config.yaml path")
    parser.add_argument("--input", type=Path, default=None, help="sales CSV path")
    parser.add_argument("--output", type=Path, default=None, help="gold CSV path")
    parser.add_argument(
        "--quarantine", type=Path, default=None, help="quarantine CSV path"
    )
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args(argv)
    setup_logging(args.log_level)

    settings = load_config(args.config)
    report = run_build(
        args.input or settings.sales_csv,
        args.output or settings.gold_csv,
        args.quarantine or settings.quarantine_csv,
        settings,
    )
    return 0 if report.rows_valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
