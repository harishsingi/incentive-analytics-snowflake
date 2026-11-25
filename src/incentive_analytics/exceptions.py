"""Error types for the incentive-analytics package.

A small hierarchy so callers (and the CLI entry points) can distinguish
a bad configuration, a bad input row, and a data-quality problem in a
source file, instead of catching a bare ``Exception`` or ``ValueError``.
"""

from __future__ import annotations


class IncentiveAnalyticsError(Exception):
    """Base error for everything this package raises deliberately."""


class ConfigurationError(IncentiveAnalyticsError):
    """Raised when configuration is missing, unreadable, or invalid."""


class ValidationError(IncentiveAnalyticsError):
    """Raised when a single input record fails schema/value validation."""


class DataQualityError(IncentiveAnalyticsError):
    """Raised when a source file is missing, empty, or structurally wrong.

    Individual bad rows are *not* raised as this error: they are
    quarantined by :mod:`incentive_analytics.validation` so one bad row
    cannot fail an otherwise usable batch.
    """
