"""Tests for tiering, variable payments, and trend flags."""

import pytest

from incentive_analytics.config import Settings
from incentive_analytics.exceptions import ValidationError
from incentive_analytics.tiers import (
    trend_flag,
    tier_for_units,
    variable_payment_estimate,
)


def test_tier_boundaries():
    assert tier_for_units(0) == "Standard"
    assert tier_for_units(249) == "Standard"
    assert tier_for_units(250) == "Gold"
    assert tier_for_units(499) == "Gold"
    assert tier_for_units(500) == "Platinum"
    assert tier_for_units(10_000) == "Platinum"


def test_tier_uses_config_thresholds():
    settings = Settings()
    custom = Settings.from_mapping(
        {"tiers": {"platinum_min_units": 100, "gold_min_units": 50}}
    )
    assert tier_for_units(75, custom) == "Gold"
    assert tier_for_units(75, settings) == "Standard"


def test_tier_rejects_negative_and_non_integer():
    with pytest.raises(ValidationError):
        tier_for_units(-1)
    with pytest.raises(ValidationError):
        tier_for_units(250.5)  # type: ignore[arg-type]


def test_variable_payment_uses_tier_rates():
    assert variable_payment_estimate(100, "Standard") == 100 * 50
    assert variable_payment_estimate(100, "Gold") == 100 * 100
    assert variable_payment_estimate(100, "Platinum") == 100 * 150
    assert variable_payment_estimate(0, "Platinum") == 0


def test_variable_payment_rejects_unknown_tier():
    with pytest.raises(ValidationError):
        variable_payment_estimate(100, "Diamond")


def test_trend_flag_thresholds():
    assert trend_flag(110, 100) == "improving"  # +10%
    assert trend_flag(90, 100) == "declining"  # -10%
    assert trend_flag(103, 100) == "flat"  # +3%, inside the 5% band
    assert trend_flag(100, 100) == "flat"
    assert trend_flag(105, 100) == "flat"  # exactly at the threshold
    assert trend_flag(106, 100) == "improving"


def test_trend_flag_no_baseline_and_zero_prior():
    assert trend_flag(100, None) == "no_baseline"
    assert trend_flag(10, 0) == "improving"
    assert trend_flag(0, 0) == "flat"
