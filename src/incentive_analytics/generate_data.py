"""Deterministic synthetic sales-data generator.

Generates several transactions per dealer per quarter (rather than
one row per dealer-quarter) so quarterly totals actually span the
Standard / Gold / Platinum tiers. All values are synthetic, drawn
from a seeded ``random.Random`` instance, so the same seed always
produces the same file.

Importing this module has no side effects: generation only happens
when :func:`main` (or :func:`generate_sales`) is called.
"""

from __future__ import annotations

import argparse
import logging
import random
from dataclasses import replace
from pathlib import Path

from .config import Settings, load_config
from .data_io import write_sales_csv
from .logging_config import setup_logging
from .models import SaleRecord
from .tiers import tier_for_units

logger = logging.getLogger(__name__)


def generate_sales(settings: Settings, seed: int | None = None) -> list[SaleRecord]:
    """Generate synthetic sales records deterministically.

    Each dealer gets ``transactions_per_quarter`` transactions in each
    configured quarter, each with a random unit count in the configured
    range. ``transaction_id`` encodes dealer, quarter, and sequence, so
    duplicates are detectable downstream.
    """
    rng = random.Random(seed if seed is not None else settings.seed)
    records: list[SaleRecord] = []
    for dealer_number in range(1, settings.dealer_count + 1):
        dealer_id = f"D{dealer_number:02d}"
        for quarter in settings.quarters:
            transaction_count = rng.randint(
                settings.transactions_per_quarter_min,
                settings.transactions_per_quarter_max,
            )
            for sequence in range(1, transaction_count + 1):
                records.append(
                    SaleRecord(
                        transaction_id=f"{dealer_id}-{quarter}-T{sequence:02d}",
                        dealer_id=dealer_id,
                        quarter=quarter,
                        units=rng.randint(
                            settings.units_per_transaction_min,
                            settings.units_per_transaction_max,
                        ),
                    )
                )
    return records


def _tier_distribution(
    records: list[SaleRecord], settings: Settings
) -> dict[str, int]:
    from collections import Counter

    totals: dict[tuple[str, str], int] = {}
    for record in records:
        key = (record.dealer_id, record.quarter)
        totals[key] = totals.get(key, 0) + record.units
    return dict(Counter(tier_for_units(total, settings) for total in totals.values()))


def main(argv: list[str] | None = None) -> int:
    """CLI entry point: ``python -m incentive_analytics generate``."""
    parser = argparse.ArgumentParser(description="Generate synthetic sales data.")
    parser.add_argument("--config", type=Path, default=None, help="config.yaml path")
    parser.add_argument("--output", type=Path, default=None, help="sales CSV path")
    parser.add_argument("--seed", type=int, default=None, help="override the seed")
    parser.add_argument("--dealers", type=int, default=None, help="override dealer count")
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args(argv)
    setup_logging(args.log_level)

    settings = load_config(args.config)
    if args.seed is not None:
        settings = replace(settings, seed=args.seed)
    if args.dealers is not None:
        settings = replace(settings, dealer_count=args.dealers)
    settings.validate()

    records = generate_sales(settings)
    output = args.output or settings.sales_csv
    write_sales_csv(
        output,
        [
            {
                "transaction_id": r.transaction_id,
                "dealer_id": r.dealer_id,
                "quarter": r.quarter,
                "units": str(r.units),
            }
            for r in records
        ],
    )
    logger.info(
        "generated %d sales rows for %d dealers x %d quarters; "
        "quarterly tier distribution: %s",
        len(records),
        settings.dealer_count,
        len(settings.quarters),
        _tier_distribution(records, settings),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
