"""CLI dispatcher: ``python -m incentive_analytics <command>``.

Subcommands: ``generate`` (synthetic sales data), ``build-gold``
(gold table), ``upload`` (optional Snowflake upload of the gold CSV).
"""

from __future__ import annotations

import argparse
import sys

from . import build_gold, generate_data
from .logging_config import setup_logging
from .snowflake_loader import SnowflakeConfig, upload_gold_csv


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="incentive_analytics")
    subparsers = parser.add_subparsers(dest="command", required=True)

    gen = subparsers.add_parser("generate", help="Generate synthetic sales data.")
    gen.add_argument("--config", default=None)
    gen.add_argument("--output", default=None)
    gen.add_argument("--seed", type=int, default=None)
    gen.add_argument("--dealers", type=int, default=None)

    build = subparsers.add_parser("build-gold", help="Build the gold bonus table.")
    build.add_argument("--config", default=None)
    build.add_argument("--input", default=None)
    build.add_argument("--output", default=None)
    build.add_argument("--quarantine", default=None)

    upload = subparsers.add_parser(
        "upload", help="Upload the gold CSV to Snowflake (optional)."
    )
    upload.add_argument("--input", default=None, help="gold CSV path")
    upload.add_argument("--table", default="GOLD_DEALER_BONUS")

    args = parser.parse_args(argv)
    setup_logging("INFO")
    if args.command == "generate":
        return generate_data.main(
            _forward(args, ("config", "output", "seed", "dealers"))
        )
    if args.command == "build-gold":
        return build_gold.main(
            _forward(args, ("config", "input", "output", "quarantine"))
        )
    upload_gold_csv(
        args.input or "data/gold.csv",
        config=SnowflakeConfig.from_env(table=args.table),
    )
    return 0


def _forward(args: argparse.Namespace, names: tuple[str, ...]) -> list[str]:
    """Rebuild an argv list from parsed subcommand options."""
    argv: list[str] = []
    for name in names:
        value = getattr(args, name, None)
        if value is not None:
            argv.extend([f"--{name}", str(value)])
    return argv


if __name__ == "__main__":
    sys.exit(main())
