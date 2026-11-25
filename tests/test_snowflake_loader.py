"""Tests for the optional Snowflake loader (no network, no credentials)."""

import pytest

from incentive_analytics.exceptions import ConfigurationError
from incentive_analytics.snowflake_loader import (
    SnowflakeConfig,
    upload_gold_csv,
)


def _env(monkeypatch):
    for name, value in {
        "SNOWFLAKE_ACCOUNT": "test-account",
        "SNOWFLAKE_USER": "test-user",
        "SNOWFLAKE_PASSWORD": "test-password",
        "SNOWFLAKE_WAREHOUSE": "test-wh",
        "SNOWFLAKE_DATABASE": "test-db",
        "SNOWFLAKE_SCHEMA": "test-schema",
    }.items():
        monkeypatch.setenv(name, value)


def test_from_env_reports_missing_variables(monkeypatch):
    monkeypatch.delenv("SNOWFLAKE_ACCOUNT", raising=False)
    with pytest.raises(ConfigurationError, match="SNOWFLAKE_ACCOUNT"):
        SnowflakeConfig.from_env()


def test_from_env_builds_config(monkeypatch):
    _env(monkeypatch)
    config = SnowflakeConfig.from_env()
    assert config.account == "test-account"
    assert config.table == "GOLD_DEALER_BONUS"


def test_upload_missing_file_raises_before_any_connection(tmp_path, monkeypatch):
    _env(monkeypatch)
    with pytest.raises(ConfigurationError, match="not found"):
        upload_gold_csv(tmp_path / "missing.csv")


def test_upload_uses_injected_connection_and_retries(tmp_path, monkeypatch):
    _env(monkeypatch)
    gold = tmp_path / "gold.csv"
    gold.write_text("dealer_id,quarter,units\nD01,2024Q1,120\n", encoding="utf-8")

    executed: list[str] = []
    attempts: list[int] = []

    class FakeCursor:
        def execute(self, sql, *args):
            executed.append(sql)

    class FakeConnection:
        def cursor(self):
            return FakeCursor()

        def close(self):
            pass

    def flaky_factory():
        attempts.append(1)
        if len(attempts) == 1:
            raise RuntimeError("transient network failure")
        return FakeConnection()

    # The retry wrapper uses real sleeps (base 1s); patch time.sleep via
    # the retry module's default by keeping attempts small: the first
    # failure sleeps ~1s once, which is acceptable for this one test.
    upload_gold_csv(gold, connection_factory=flaky_factory)
    assert len(attempts) == 2
    assert any("PUT file://" in sql for sql in executed)
    assert any("COPY INTO test-db.test-schema.GOLD_DEALER_BONUS" in sql for sql in executed)
