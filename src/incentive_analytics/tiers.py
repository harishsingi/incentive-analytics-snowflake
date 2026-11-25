"""Bonus tiering, variable-payment estimates, and trend flags.

Pure functions: no I/O, no global state. Thresholds and rates come
from :class:`incentive_analytics.config.Settings` so the Python logic
and ``sql/bonus_gold.sql`` can be kept in agreement (see the header
comment in that SQL file).
"""

from __future__ import annotations

from .config import Settings
from .exceptions import ValidationError

PLATINUM = "Platinum"
GOLD = "Gold"
STANDARD = "Standard"

IMPROVING = "improving"
FLAT = "flat"
DECLINING = "declining"
NO_BASELINE = "no_baseline"


def tier_for_units(units: int, settings: Settings | None = None) -> str:
    """Return the bonus tier for a quarterly unit total.

    Platinum at or above the platinum threshold, Gold at or above the
    gold threshold, otherwise Standard. A negative total is a caller
    bug, not a tier, so it raises ValidationError.
    """
    if isinstance(units, bool) or not isinstance(units, int):
        raise ValidationError(f"units must be an integer, got {units!r}")
    if units < 0:
        raise ValidationError(f"units must be >= 0, got {units}")
    cfg = settings or Settings()
    if units >= cfg.tiers.platinum_min_units:
        return PLATINUM
    if units >= cfg.tiers.gold_min_units:
        return GOLD
    return STANDARD


def variable_payment_estimate(
    units: int, tier: str, settings: Settings | None = None
) -> int:
    """Illustrative synthetic variable-payment estimate for a tier.

    ``units * rate`` with the per-unit rate from settings. The rates
    are synthetic demo parameters, not real bonus rates.
    """
    if tier not in (PLATINUM, GOLD, STANDARD):
        raise ValidationError(f"unknown bonus tier: {tier!r}")
    if units < 0:
        raise ValidationError(f"units must be >= 0, got {units}")
    cfg = settings or Settings()
    rates = {
        PLATINUM: cfg.variable_payment_per_unit.platinum,
        GOLD: cfg.variable_payment_per_unit.gold,
        STANDARD: cfg.variable_payment_per_unit.standard,
    }
    return units * rates[tier]


def trend_flag(
    current_units: int,
    prior_year_units: int | None,
    threshold_pct: float = 0.05,
) -> str:
    """Compare a quarter with the same quarter last year.

    Returns ``"improving"`` / ``"flat"`` / ``"declining"`` when the
    change exceeds the threshold in either direction, and
    ``"no_baseline"`` when there is no prior-year quarter to compare
    with (for example the first year in the data). A prior-year total
    of zero with any current units counts as improving.
    """
    if prior_year_units is None:
        return NO_BASELINE
    if current_units < 0 or prior_year_units < 0:
        raise ValidationError("unit totals must be >= 0 for a trend comparison")
    if prior_year_units == 0:
        return IMPROVING if current_units > 0 else FLAT
    change = (current_units - prior_year_units) / prior_year_units
    if change > threshold_pct:
        return IMPROVING
    if change < -threshold_pct:
        return DECLINING
    return FLAT
