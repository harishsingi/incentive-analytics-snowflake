"""Retry with exponential backoff and jitter.

Used for operations that can fail transiently (the optional Snowflake
upload in :mod:`snowflake_loader`). Local CSV work does not need
retries and does not use this module: retrying a deterministic local
failure would only waste time.

The decorator never retries a deliberately raised
:class:`incentive_analytics.exceptions.IncentiveAnalyticsError` unless
the caller explicitly lists it, so configuration and validation errors
fail fast instead of being retried.
"""

from __future__ import annotations

import functools
import logging
import random
import time
from typing import Callable, ParamSpec, TypeVar

from .exceptions import IncentiveAnalyticsError

P = ParamSpec("P")
T = TypeVar("T")

logger = logging.getLogger(__name__)


def retry_with_backoff(
    max_attempts: int = 3,
    base_delay_seconds: float = 1.0,
    max_delay_seconds: float = 30.0,
    retry_on: tuple[type[BaseException], ...] = (Exception,),
    _sleep: Callable[[float], None] = time.sleep,
    _rng: random.Random | None = None,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Decorate a callable with bounded retries and backoff.

    Delays grow as ``base * 2**attempt`` (capped at ``max_delay``)
    plus up to 10% jitter. After ``max_attempts`` failures the last
    exception is raised unchanged. ``max_attempts`` must be >= 1.
    """
    if max_attempts < 1:
        raise ValueError(f"max_attempts must be >= 1, got {max_attempts}")
    if base_delay_seconds < 0 or max_delay_seconds < 0:
        raise ValueError("delays must be >= 0")
    rng = _rng or random.Random()

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            last_error: BaseException | None = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except retry_on as exc:
                    if isinstance(exc, IncentiveAnalyticsError) and (
                        IncentiveAnalyticsError not in retry_on
                        and type(exc) not in retry_on
                    ):
                        raise
                    last_error = exc
                    if attempt == max_attempts:
                        break
                    delay = min(
                        base_delay_seconds * (2 ** (attempt - 1)),
                        max_delay_seconds,
                    )
                    delay += rng.uniform(0, delay * 0.1)
                    logger.warning(
                        "%s failed on attempt %d/%d (%s); retrying in %.2fs",
                        func.__name__,
                        attempt,
                        max_attempts,
                        exc,
                        delay,
                    )
                    _sleep(delay)
            assert last_error is not None  # max_attempts >= 1 guarantees this
            raise last_error

        return wrapper

    return decorator
