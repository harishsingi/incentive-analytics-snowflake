"""Tests for logging setup and the public package surface."""

import logging

import incentive_analytics
from incentive_analytics.logging_config import setup_logging


def test_setup_logging_is_idempotent():
    logger = setup_logging("INFO")
    first_handler_count = len(logging.getLogger().handlers)
    setup_logging("INFO")
    assert len(logging.getLogger().handlers) == first_handler_count
    assert logger.name == "incentive_analytics"


def test_package_exports():
    assert incentive_analytics.__version__ == "0.2.0"
    for name in ("Settings", "SaleRecord", "GoldRow", "tier_for_units"):
        assert hasattr(incentive_analytics, name)
