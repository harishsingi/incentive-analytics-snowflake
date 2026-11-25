"""Optional Snowflake upload for the gold table.

This is an integration point, not a required step: the local pipeline
and all tests run without Snowflake, without credentials, and without
any network access.

When used, credentials come only from environment variables
(``SNOWFLAKE_ACCOUNT``, ``SNOWFLAKE_USER``, ``SNOWFLAKE_PASSWORD``,
``SNOWFLAKE_WAREHOUSE``, ``SNOWFLAKE_DATABASE``, ``SNOWFLAKE_SCHEMA``)
and are never logged, written to a file, or hardcoded. The upload
attempt is wrapped in :func:`retry_with_backoff` because a failed
``PUT``/``COPY`` is the one place in this project where a transient
network error is plausible. ``snowflake-connector-python`` is an
optional dependency: if it is not installed, a clear
ConfigurationError is raised before any network attempt.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Protocol

from .exceptions import ConfigurationError
from .retry import retry_with_backoff

logger = logging.getLogger(__name__)

REQUIRED_ENV_VARS: tuple[str, ...] = (
    "SNOWFLAKE_ACCOUNT",
    "SNOWFLAKE_USER",
    "SNOWFLAKE_PASSWORD",
    "SNOWFLAKE_WAREHOUSE",
    "SNOWFLAKE_DATABASE",
    "SNOWFLAKE_SCHEMA",
)


class _Cursor(Protocol):
    def execute(self, sql: str, *args: object) -> object: ...


class _Connection(Protocol):
    def cursor(self) -> _Cursor: ...
    def close(self) -> None: ...


ConnectionFactory = Callable[[], _Connection]


@dataclass(frozen=True)
class SnowflakeConfig:
    """Connection details, built only from environment variables."""

    account: str
    user: str
    warehouse: str
    database: str
    schema: str
    table: str = "GOLD_DEALER_BONUS"
    role: str | None = None

    @classmethod
    def from_env(cls, table: str = "GOLD_DEALER_BONUS") -> "SnowflakeConfig":
        """Build from the environment; password is read separately.

        Missing variables are listed by name. Values are never logged.
        """
        missing = [name for name in REQUIRED_ENV_VARS if not os.environ.get(name)]
        if missing:
            raise ConfigurationError(
                "missing Snowflake environment variable(s): " + ", ".join(missing)
            )
        return cls(
            account=os.environ["SNOWFLAKE_ACCOUNT"],
            user=os.environ["SNOWFLAKE_USER"],
            warehouse=os.environ["SNOWFLAKE_WAREHOUSE"],
            database=os.environ["SNOWFLAKE_DATABASE"],
            schema=os.environ["SNOWFLAKE_SCHEMA"],
            table=table,
            role=os.environ.get("SNOWFLAKE_ROLE") or None,
        )


def _default_connection_factory(config: SnowflakeConfig) -> ConnectionFactory:
    def factory() -> _Connection:
        try:
            import snowflake.connector
        except ImportError as exc:
            raise ConfigurationError(
                "snowflake-connector-python is not installed; "
                "install it with: pip install snowflake-connector-python"
            ) from exc
        return snowflake.connector.connect(
            account=config.account,
            user=config.user,
            password=os.environ["SNOWFLAKE_PASSWORD"],
            warehouse=config.warehouse,
            database=config.database,
            schema=config.schema,
            role=config.role,
        )

    return factory


def upload_gold_csv(
    csv_path: str | Path,
    config: SnowflakeConfig | None = None,
    connection_factory: ConnectionFactory | None = None,
) -> None:
    """Upload a gold CSV into Snowflake with retry on transient errors.

    Stages the file with ``PUT`` and loads it with ``COPY INTO``,
    matching the gold columns written by :mod:`data_io`. The
    ``connection_factory`` parameter exists so tests can inject a fake
    connection; production callers omit it.
    """
    path = Path(csv_path)
    if not path.exists():
        raise ConfigurationError(f"gold file not found: {path}")
    cfg = config or SnowflakeConfig.from_env()
    factory = connection_factory or _default_connection_factory(cfg)
    qualified_table = f"{cfg.database}.{cfg.schema}.{cfg.table}"

    @retry_with_backoff(max_attempts=3, base_delay_seconds=1.0)
    def _attempt() -> None:
        connection = factory()
        try:
            cursor = connection.cursor()
            cursor.execute(f"PUT file://{path} @%{cfg.table}")
            cursor.execute(
                "COPY INTO "
                f"{qualified_table} "
                "(dealer_id, quarter, units, bonus_tier, "
                "variable_payment_estimate, trend_flag, prior_year_units) "
                "FILE_FORMAT = (TYPE = CSV SKIP_HEADER = 1)"
            )
        finally:
            connection.close()

    _attempt()
    logger.info("uploaded %s to Snowflake table %s", path, qualified_table)
