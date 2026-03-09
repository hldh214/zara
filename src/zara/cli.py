from __future__ import annotations

import argparse
import asyncio
import sys

from loguru import logger

from zara import config
from zara.scanner import run_scan


def _run_scheduler() -> None:
    """Start the APScheduler blocking scheduler for daily scans."""
    from apscheduler.schedulers.blocking import BlockingScheduler
    from apscheduler.triggers.cron import CronTrigger

    scheduler = BlockingScheduler()

    def _job() -> None:
        asyncio.run(run_scan())

    trigger = CronTrigger(
        hour=config.SCHEDULE_HOUR,
        minute=config.SCHEDULE_MINUTE,
        timezone=config.TIMEZONE,
    )

    scheduler.add_job(_job, trigger, id="zara_scan", name="Zara JP Discount Scan")

    logger.info(
        "Scheduler started. Will run daily at {:02d}:{:02d} ({})",
        config.SCHEDULE_HOUR,
        config.SCHEDULE_MINUTE,
        config.TIMEZONE,
    )
    logger.info("Discount threshold: >= {}% off", config.DISCOUNT_THRESHOLD)
    logger.info("Concurrency: {} simultaneous requests", config.CONCURRENCY)
    logger.info("Press Ctrl+C to stop.")

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Zara JP discount monitor - find sale items on zara.com/jp",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run a single scan immediately and exit (no scheduler)",
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

    if args.once:
        asyncio.run(run_scan())
        sys.exit(0)
    else:
        _run_scheduler()


if __name__ == "__main__":
    main()
