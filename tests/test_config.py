"""Tests for config loading and validation."""

import pytest

from incentive_analytics.config import Settings, load_config
from incentive_analytics.exceptions import ConfigurationError


def test_defaults_match_config_yaml():
    from pathlib import Path

    loaded = load_config(Path(__file__).resolve().parents[1] / "config.yaml")
    assert loaded == Settings()
    assert loaded.seed == 19
    assert loaded.dealer_count == 30
    assert loaded.tiers.platinum_min_units == 500
    assert loaded.tiers.gold_min_units == 250


def test_load_config_from_yaml(tmp_path):
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        "seed: 7\ndealer_count: 2\nquarters: [2025Q1]\n"
        "tiers: {platinum_min_units: 100, gold_min_units: 50}\n",
        encoding="utf-8",
    )
    settings = load_config(config_file)
    assert settings.seed == 7
    assert settings.dealer_count == 2
    assert settings.quarters == ("2025Q1",)
    assert settings.tiers.platinum_min_units == 100


def test_load_config_missing_explicit_file_raises(tmp_path):
    with pytest.raises(ConfigurationError):
        load_config(tmp_path / "does-not-exist.yaml")


def test_load_config_no_file_returns_defaults(tmp_path, monkeypatch):
    monkeypatch.setenv("INCENTIVE_CONFIG", str(tmp_path / "missing.yaml"))
    with pytest.raises(ConfigurationError):
        load_config()
    monkeypatch.delenv("INCENTIVE_CONFIG")
    # Default location (repo config.yaml) exists, so defaults load.
    assert load_config().seed == 19


def test_env_seed_override(monkeypatch):
    monkeypatch.setenv("INCENTIVE_SEED", "42")
    assert load_config().seed == 42


def test_env_seed_must_be_integer(monkeypatch):
    monkeypatch.setenv("INCENTIVE_SEED", "not-a-number")
    with pytest.raises(ConfigurationError):
        load_config()


def test_invalid_thresholds_rejected():
    with pytest.raises(ConfigurationError):
        Settings.from_mapping(
            {"tiers": {"platinum_min_units": 100, "gold_min_units": 100}}
        )
    with pytest.raises(ConfigurationError):
        Settings.from_mapping({"trend_threshold_pct": 1.5})
    with pytest.raises(ConfigurationError):
        Settings.from_mapping({"dealer_count": 0})
    with pytest.raises(ConfigurationError):
        Settings.from_mapping({"variable_payment_per_unit": {"standard": -1}})
