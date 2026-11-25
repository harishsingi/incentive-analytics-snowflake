"""Tests for retry-with-backoff."""

import pytest

from incentive_analytics.exceptions import ConfigurationError
from incentive_analytics.retry import retry_with_backoff


def test_retry_succeeds_after_transient_failures():
    attempts: list[int] = []
    delays: list[float] = []

    @retry_with_backoff(
        max_attempts=3, base_delay_seconds=0, _sleep=delays.append
    )
    def flaky():
        attempts.append(1)
        if len(attempts) < 3:
            raise RuntimeError("transient")
        return "ok"

    assert flaky() == "ok"
    assert len(attempts) == 3
    assert delays == [0.0, 0.0] or all(d >= 0 for d in delays)


def test_retry_exhausts_and_raises_last_error():
    calls: list[int] = []

    @retry_with_backoff(max_attempts=2, base_delay_seconds=0, _sleep=lambda _: None)
    def always_fails():
        calls.append(1)
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError, match="boom"):
        always_fails()
    assert len(calls) == 2


def test_retry_does_not_retry_configuration_errors_by_default():
    calls: list[int] = []

    @retry_with_backoff(max_attempts=3, base_delay_seconds=0, _sleep=lambda _: None)
    def bad_config():
        calls.append(1)
        raise ConfigurationError("bad config")

    with pytest.raises(ConfigurationError):
        bad_config()
    assert len(calls) == 1  # failed fast, no retries


def test_retry_rejects_invalid_max_attempts():
    with pytest.raises(ValueError):
        retry_with_backoff(max_attempts=0)
