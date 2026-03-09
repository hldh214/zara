from __future__ import annotations

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


def run_scan() -> None:
    """Execute a full scan: fetch all products, filter by discount, and report in real-time."""
    threshold = config.DISCOUNT_THRESHOLD
    logger.info("Starting Zara JP discount scan (threshold: >= {}% off)", threshold)

    with httpx.Client(
        headers=HEADERS, timeout=config.REQUEST_TIMEOUT, follow_redirects=True
    ) as client:
        categories = fetch_categories(client)
        cat_ids = get_product_category_ids(categories)
        logger.info("Found {} product categories to scan", len(cat_ids))

        seen_ids: set[int] = set()
        total_products = 0
        total_hits = 0

        for i, (cat_id, cat_name) in enumerate(cat_ids):
            products = fetch_products_for_category(client, cat_id, cat_name)

            # Deduplicate and check threshold immediately
            new_products: list[Product] = []
            for p in products:
                if p.id not in seen_ids:
                    seen_ids.add(p.id)
                    new_products.append(p)

            total_products += len(new_products)

            # Report discounted items for this category right away
            for p in new_products:
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

            if (i + 1) % 50 == 0:
                logger.info("Progress: {}/{} categories scanned", i + 1, len(cat_ids))

            time.sleep(config.REQUEST_DELAY)

        logger.info(
            "Scan complete. {} unique products scanned, {} items matched threshold (>= {}% off)",
            total_products,
            total_hits,
            threshold,
        )
