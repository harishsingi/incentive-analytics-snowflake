"""Configuration, separated from pipeline logic.

Settings come from ``config.yaml`` at the repository root (loaded with
PyYAML), with ``INCENTIVE_CONFIG`` overriding the file location and
``INCENTIVE_SEED`` overriding the synthetic-data seed. If no config file
exists, the documented defaults below are used, so the package still
runs from a bare checkout.

No credentials live here or in ``config.yaml``: Snowflake credentials,
when used at all, come only from environment variables (see
``snowflake_loader``) and are never logged.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover - exercised only without PyYAML
    yaml = None

from .exceptions import ConfigurationError

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[2] / "config.yaml"

DEFAULT_QUARTERS: tuple[str, ...] = (
    "2024Q1",
    "2024Q2",
    "2024Q3",
    "2024Q4",
    "2025Q1",
    "2025Q2",
    "2025Q3",
    "2025Q4",
)


@dataclass(frozen=True)
class TierThresholds:
    """Minimum quarterly units for each bonus tier."""

    platinum_min_units: int = 500
    gold_min_units: int = 250

    def validate(self) -> None:
        if self.platinum_min_units <= self.gold_min_units:
            raise ConfigurationError(
                "platinum_min_units must be greater than gold_min_units: "
                f"got {self.platinum_min_units} and {self.gold_min_units}"
            )
        if self.gold_min_units <= 0:
            raise ConfigurationError(
                f"gold_min_units must be positive, got {self.gold_min_units}"
            )


@dataclass(frozen=True)
class VariablePaymentRates:
    """Illustrative synthetic payment per unit, by tier.

    These are invented parameters for synthetic demo data only. They
    are not real dealer bonus rates from any organisation.
    """

    platinum: int = 150
    gold: int = 100
    standard: int = 50

    def validate(self) -> None:
        for name, value in (
            ("platinum", self.platinum),
            ("gold", self.gold),
            ("standard", self.standard),
        ):
            if value < 0:
                raise ConfigurationError(
                    f"variable payment rate for {name} must be >= 0, got {value}"
                )


@dataclass(frozen=True)
class Settings:
    """All tunable behaviour for generation and gold-table builds."""

    seed: int = 19
    dealer_count: int = 30
    quarters: tuple[str, ...] = DEFAULT_QUARTERS
    transactions_per_quarter_min: int = 3
    transactions_per_quarter_max: int = 6
    units_per_transaction_min: int = 40
    units_per_transaction_max: int = 180
    tiers: TierThresholds = field(default_factory=TierThresholds)
    variable_payment_per_unit: VariablePaymentRates = field(
        default_factory=VariablePaymentRates
    )
    trend_threshold_pct: float = 0.05
    sales_csv: Path = Path("data/sales.csv")
    gold_csv: Path = Path("data/gold.csv")
    quarantine_csv: Path = Path("data/quarantine.csv")

    def validate(self) -> None:
        """Raise ConfigurationError on any inconsistent setting."""
        if self.dealer_count <= 0:
            raise ConfigurationError(f"dealer_count must be positive, got {self.dealer_count}")
        if not self.quarters:
            raise ConfigurationError("quarters must not be empty")
        if self.transactions_per_quarter_min < 1:
            raise ConfigurationError(
                "transactions_per_quarter_min must be >= 1, "
                f"got {self.transactions_per_quarter_min}"
            )
        if self.transactions_per_quarter_max < self.transactions_per_quarter_min:
            raise ConfigurationError(
                "transactions_per_quarter_max must be >= "
                "transactions_per_quarter_min"
            )
        if self.units_per_transaction_min < 0:
            raise ConfigurationError("units_per_transaction_min must be >= 0")
        if self.units_per_transaction_max < self.units_per_transaction_min:
            raise ConfigurationError(
                "units_per_transaction_max must be >= units_per_transaction_min"
            )
        if not 0 <= self.trend_threshold_pct < 1:
            raise ConfigurationError(
                "trend_threshold_pct must be in [0, 1), "
                f"got {self.trend_threshold_pct}"
            )
        self.tiers.validate()
        self.variable_payment_per_unit.validate()

    @classmethod
    def from_mapping(cls, mapping: dict) -> "Settings":
        """Build settings from a parsed config file mapping."""
        if not isinstance(mapping, dict):
            raise ConfigurationError("config file must contain a mapping")
        tiers = mapping.get("tiers", {}) or {}
        rates = mapping.get("variable_payment_per_unit", {}) or {}
        tx = mapping.get("transactions_per_quarter", {}) or {}
        units = mapping.get("units_per_transaction", {}) or {}
        paths = mapping.get("paths", {}) or {}
        settings = cls(
            seed=int(mapping.get("seed", 19)),
            dealer_count=int(mapping.get("dealer_count", 30)),
            quarters=tuple(mapping.get("quarters", DEFAULT_QUARTERS)),
            transactions_per_quarter_min=int(tx.get("min", 3)),
            transactions_per_quarter_max=int(tx.get("max", 6)),
            units_per_transaction_min=int(units.get("min", 40)),
            units_per_transaction_max=int(units.get("max", 180)),
            tiers=TierThresholds(
                platinum_min_units=int(tiers.get("platinum_min_units", 500)),
                gold_min_units=int(tiers.get("gold_min_units", 250)),
            ),
            variable_payment_per_unit=VariablePaymentRates(
                platinum=int(rates.get("platinum", 150)),
                gold=int(rates.get("gold", 100)),
                standard=int(rates.get("standard", 50)),
            ),
            trend_threshold_pct=float(mapping.get("trend_threshold_pct", 0.05)),
            sales_csv=Path(paths.get("sales_csv", "data/sales.csv")),
            gold_csv=Path(paths.get("gold_csv", "data/gold.csv")),
            quarantine_csv=Path(paths.get("quarantine_csv", "data/quarantine.csv")),
        )
        settings.validate()
        return settings


def load_config(path: str | Path | None = None) -> Settings:
    """Load settings from a YAML file, an env override, or the defaults.

    Resolution order: explicit ``path`` argument, then the
    ``INCENTIVE_CONFIG`` environment variable, then ``config.yaml`` at
    the repository root. If no file exists at the resolved default
    location, the documented defaults are returned. An explicitly
    requested file that does not exist is an error.
    """
    env_path = os.environ.get("INCENTIVE_CONFIG")
    if path is not None:
        config_path = Path(path)
        explicit = True
    elif env_path:
        config_path = Path(env_path)
        explicit = True
    else:
        config_path = DEFAULT_CONFIG_PATH
        explicit = False
    if not config_path.exists():
        if explicit:
            raise ConfigurationError(f"config file not found: {config_path}")
        settings = Settings()
        settings.validate()
        return _apply_env_overrides(settings)
    if yaml is None:
        raise ConfigurationError(
            "PyYAML is required to read config.yaml; "
            "install it with: pip install -r requirements.txt"
        )
    with config_path.open("r", encoding="utf-8") as handle:
        mapping = yaml.safe_load(handle) or {}
    settings = Settings.from_mapping(mapping)
    return _apply_env_overrides(settings)


def _apply_env_overrides(settings: Settings) -> Settings:
    """Apply the small set of supported environment overrides."""
    seed = os.environ.get("INCENTIVE_SEED")
    if seed is None:
        return settings
    try:
        seed_value = int(seed)
    except ValueError as exc:
        raise ConfigurationError(
            f"INCENTIVE_SEED must be an integer, got {seed!r}"
        ) from exc
    from dataclasses import replace

    overridden = replace(settings, seed=seed_value)
    overridden.validate()
    return overridden
