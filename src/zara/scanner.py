from __future__ import annotations

import asyncio
import time

import httpx
from loguru import logger

from zara import config
from zara.client import (
    Product,
    fetch_categories,
    fetch_products_for_category,
    get_product_category_ids,
    HEADERS,
)
from zara.notify import notify, notify_summary


async def _fetch_one(
    client: httpx.AsyncClient,
    semaphore: asyncio.Semaphore,
    cat_id: int,
    cat_name: str,
) -> list[Product]:
    """Fetch products for one category, rate-limited by semaphore."""
    async with semaphore:
        products = await fetch_products_for_category(client, cat_id, cat_name)
        await asyncio.sleep(config.REQUEST_DELAY)
        return products


async def run_scan() -> None:
    """Execute a full scan: fetch all products, filter by discount, and report in real-time."""
    threshold = config.DISCOUNT_THRESHOLD
    concurrency = config.CONCURRENCY
    logger.info(
        "Starting Zara JP discount scan (threshold: >= {}% off, concurrency: {})",
        threshold,
        concurrency,
    )

    async with httpx.AsyncClient(
        headers=HEADERS, timeout=config.REQUEST_TIMEOUT, follow_redirects=True
    ) as client:
        categories = await fetch_categories(client)
        cat_ids = get_product_category_ids(categories)
        logger.info("Found {} product categories to scan", len(cat_ids))

        seen_ids: set[int] = set()
        total_products = 0
        total_hits = 0
        scanned = 0

        semaphore = asyncio.Semaphore(concurrency)

        # Create all tasks upfront
        tasks = {
            asyncio.create_task(_fetch_one(client, semaphore, cat_id, cat_name)): (
                cat_id,
                cat_name,
            )
            for cat_id, cat_name in cat_ids
        }

        start = time.monotonic()

        for coro in asyncio.as_completed(tasks):
            products = await coro
            scanned += 1

            # Deduplicate and check threshold immediately
            for p in products:
                if p.id in seen_ids:
                    continue
                seen_ids.add(p.id)
                total_products += 1

                if (
                    p.is_on_sale
                    and p.discount_pct is not None
                    and p.discount_pct >= threshold
                ):
                    total_hits += 1
                    logger.success(
                        "[{}] {} | ¥{:,} (was ¥{:,}, -{}% off) | {}",
                        p.section,
                        p.name,
                        p.price,
                        p.old_price,
                        p.discount_pct,
                        p.url,
                    )
                    await notify(p)

            if scanned % 50 == 0:
                elapsed = time.monotonic() - start
                logger.info(
                    "Progress: {}/{} categories scanned ({:.0f}s elapsed)",
                    scanned,
                    len(cat_ids),
                    elapsed,
                )

        elapsed = time.monotonic() - start
        logger.info(
            "Scan complete in {:.0f}s. {} unique products scanned, {} items matched threshold (>= {}% off)",
            elapsed,
            total_products,
            total_hits,
            threshold,
        )
        await notify_summary(total_products, total_hits, threshold)
