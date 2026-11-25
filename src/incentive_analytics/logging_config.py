"""Logging setup.

One place owns the log format so every module logs the same way.
``print`` is not used for progress or metrics anywhere in this package.
"""

from __future__ import annotations

import logging
import sys

_LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"


def setup_logging(level: str | int = "INFO") -> logging.Logger:
    """Configure the root logger once and return this package's logger.

    Calling it twice does not add duplicate handlers.
    """
    root = logging.getLogger()
    if not root.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(_LOG_FORMAT))
        root.addHandler(handler)
    root.setLevel(level)
    return logging.getLogger("incentive_analytics")
