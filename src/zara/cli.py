from __future__ import annotations

import argparse
import asyncio
import sys

from loguru import logger

from zara import config
from zara.scanner import run_scan


def main() -> None:
    """Run a single Zara JP discount scan."""
    parser = argparse.ArgumentParser(
        description="Zara JP discount monitor - find sale items on zara.com/jp",
    )
    parser.add_argument(
        "--threshold",
        type=int,
        default=None,
        help=f"Minimum discount percentage to report (default: {config.DISCOUNT_THRESHOLD})",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=None,
        help=f"Number of concurrent category fetches (default: {config.CONCURRENCY})",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable debug logging",
    )

    args = parser.parse_args()

    # Configure loguru level
    logger.remove()
    level = "DEBUG" if args.verbose else "INFO"
    logger.add(sys.stderr, level=level)

    # Override config if provided via CLI
    if args.threshold is not None:
        config.DISCOUNT_THRESHOLD = args.threshold
    if args.concurrency is not None:
        config.CONCURRENCY = args.concurrency

    asyncio.run(run_scan())


if __name__ == "__main__":
    main()
