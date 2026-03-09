from __future__ import annotations

import httpx
from loguru import logger

from zara import config
from zara.client import Product

_TG_API = "https://api.telegram.org"


def _is_enabled() -> bool:
    return bool(config.TG_BOT_TOKEN and config.TG_CHAT_ID)


def _format_message(product: Product) -> str:
    """Format a product into a Telegram HTML message."""
    lines = [
        f"<b>[{product.section}] {product.name}</b>",
        f"Price: <b>¥{product.price:,}</b>  (was ¥{product.old_price:,}, <b>-{product.discount_pct}% off</b>)",
    ]
    if product.url:
        lines.append(f'<a href="{product.url}">View on Zara</a>')
    return "\n".join(lines)


async def notify(product: Product) -> None:
    """Send a single product notification to Telegram (with photo if available)."""
    if not _is_enabled():
        return

    caption = _format_message(product)

    try:
        async with httpx.AsyncClient() as client:
            if product.image_url:
                # sendPhoto with the image URL and caption
                url = f"{_TG_API}/bot{config.TG_BOT_TOKEN}/sendPhoto"
                payload = {
                    "chat_id": config.TG_CHAT_ID,
                    "photo": product.image_url,
                    "caption": caption,
                    "parse_mode": "HTML",
                }
                resp = await client.post(url, json=payload, timeout=15)
                if resp.is_success:
                    return
                # If sendPhoto fails (e.g. image URL issue), fall back to text
                logger.debug(
                    "sendPhoto failed ({}), falling back to sendMessage",
                    resp.status_code,
                )

            # Fallback: plain text message
            url = f"{_TG_API}/bot{config.TG_BOT_TOKEN}/sendMessage"
            payload = {
                "chat_id": config.TG_CHAT_ID,
                "text": caption,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            }
            resp = await client.post(url, json=payload, timeout=10)
            if not resp.is_success:
                logger.warning("Telegram API error: {} {}", resp.status_code, resp.text)
    except Exception as exc:
        logger.warning("Failed to send Telegram notification: {}", exc)


async def notify_batch(products: list[Product]) -> None:
    """Send a batch of products as a single Telegram message."""
    if not _is_enabled() or not products:
        return

    parts = [_format_message(p) for p in products]
    text = "\n\n".join(parts)

    # Telegram message limit is 4096 chars, split if needed
    await _send_text(text)


async def notify_summary(total_products: int, total_hits: int, threshold: int) -> None:
    """Send a scan summary to Telegram."""
    if not _is_enabled():
        return

    text = (
        f"<b>Zara JP Scan Complete</b>\n"
        f"Products scanned: {total_products:,}\n"
        f"Deals found (>= {threshold}% off): <b>{total_hits}</b>"
    )
    await _send_text(text)


async def _send_text(text: str) -> None:
    """Send text to Telegram, splitting into chunks if too long."""
    url = f"{_TG_API}/bot{config.TG_BOT_TOKEN}/sendMessage"
    # Telegram limit is 4096 chars per message
    chunks = _split_text(text, 4096)

    async with httpx.AsyncClient() as client:
        for chunk in chunks:
            payload = {
                "chat_id": config.TG_CHAT_ID,
                "text": chunk,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            }
            try:
                resp = await client.post(url, json=payload, timeout=10)
                if not resp.is_success:
                    logger.warning(
                        "Telegram API error: {} {}", resp.status_code, resp.text
                    )
            except Exception as exc:
                logger.warning("Failed to send Telegram notification: {}", exc)


def _split_text(text: str, limit: int) -> list[str]:
    """Split text into chunks that fit within the limit, breaking at newlines."""
    if len(text) <= limit:
        return [text]

    chunks: list[str] = []
    while text:
        if len(text) <= limit:
            chunks.append(text)
            break
        # Find last newline within limit
        cut = text.rfind("\n", 0, limit)
        if cut == -1:
            cut = limit
        chunks.append(text[:cut])
        text = text[cut:].lstrip("\n")
    return chunks
