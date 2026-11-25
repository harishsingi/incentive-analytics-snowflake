"""Incentive analytics (Snowflake-style dealer bonus pipeline).

Local, standard-library-only implementation of the pipeline described in
``sql/bonus_gold.sql``: synthetic dealer sales are validated, aggregated
per dealer per quarter, tiered, and written as a dashboard-ready gold
table, with bad records quarantined instead of silently dropped.

All data is synthetic. No real dealer, customer, payment, or bonus
figures are included, and no credentials are stored anywhere in this
repository. A live Snowflake connection is optional (see
``snowflake_loader``) and is never required to run or test this package.
"""

from __future__ import annotations

from .config import Settings
from .exceptions import (
    ConfigurationError,
    DataQualityError,
    IncentiveAnalyticsError,
    ValidationError,
)
from .models import DataQualityReport, GoldRow, SaleRecord
from .tiers import tier_for_units, trend_flag, variable_payment_estimate

__version__ = "0.2.0"

__all__ = [
    "ConfigurationError",
    "DataQualityError",
    "DataQualityReport",
    "GoldRow",
    "IncentiveAnalyticsError",
    "SaleRecord",
    "Settings",
    "ValidationError",
    "__version__",
    "tier_for_units",
    "trend_flag",
    "variable_payment_estimate",
]
