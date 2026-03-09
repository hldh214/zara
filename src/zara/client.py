from __future__ import annotations

from dataclasses import dataclass

import httpx
from loguru import logger

from zara import config

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
    "Accept-Language": "ja",
}


# Width used when building resized image URLs (px)
_IMAGE_WIDTH = 563


@dataclass
class Product:
    id: int
    name: str
    section: str
    category: str
    price: int
    old_price: int | None
    discount_pct: int | None
    url: str
    image_url: str

    @property
    def is_on_sale(self) -> bool:
        return (
            self.old_price is not None
            and self.discount_pct is not None
            and self.discount_pct > 0
        )


async def fetch_categories(client: httpx.AsyncClient) -> list[dict]:
    """Fetch the full category tree from Zara JP."""
    url = f"{config.BASE_URL}/categories?ajax=true"
    logger.info("Fetching category tree...")
    resp = await client.get(url)
    resp.raise_for_status()
    data = resp.json()
    return data.get("categories", [])


def _collect_product_categories(node: dict, result: list[dict]) -> None:
    """Recursively walk the category tree and collect all product categories."""
    layout = node.get("layout", "")
    is_divider = node.get("attributes", {}).get("isDivider", False)
    irrelevant = node.get("irrelevant", True)

    if layout in config.PRODUCT_LAYOUTS and not is_divider and not irrelevant:
        if not node.get("isRedirected", False):
            result.append(node)

    for sub in node.get("subcategories", []):
        _collect_product_categories(sub, result)


def get_product_category_ids(categories: list[dict]) -> list[tuple[int, str]]:
    """Return a deduplicated list of (category_id, category_name) for product pages."""
    leaves: list[dict] = []
    for top in categories:
        _collect_product_categories(top, leaves)

    seen: set[int] = set()
    result: list[tuple[int, str]] = []
    for cat in leaves:
        cat_id = cat["id"]
        if cat_id not in seen:
            seen.add(cat_id)
            result.append((cat_id, cat.get("name", str(cat_id))))
    return result


def _build_product_url(product: dict) -> str:
    """Build a Zara product URL from SEO data."""
    seo = product.get("seo", {})
    keyword = seo.get("keyword", "")
    seo_id = seo.get("seoProductId", "")
    if keyword and seo_id:
        return f"{config.BASE_URL}/{keyword}-p{seo_id}.html"
    return ""


def _extract_image_url(comp: dict) -> str:
    """Extract the primary product image URL from the first color's xmedia.

    Prefers ``kind == "full"`` (the hero shot); falls back to the first
    xmedia entry.  The ``url`` field contains a ``{width}`` placeholder
    that we replace with a reasonable size for Telegram previews.
    """
    colors = comp.get("detail", {}).get("colors", [])
    if not colors:
        return ""

    xmedia = colors[0].get("xmedia", [])
    if not xmedia:
        return ""

    # Pick the main product image (kind == "full"), fall back to first
    chosen = next((m for m in xmedia if m.get("kind") == "full"), xmedia[0])

    url: str = chosen.get("url", "")
    if url and "{width}" in url:
        url = url.replace("{width}", str(_IMAGE_WIDTH))
    return url


def _parse_products_from_response(data: dict, category_name: str) -> list[Product]:
    """Parse product data from a category products API response."""
    products: list[Product] = []
    for group in data.get("productGroups", []):
        for element in group.get("elements", []):
            for comp in element.get("commercialComponents", []):
                if comp.get("type") != "Product":
                    continue

                product_id = comp.get("id")
                name = comp.get("name", "")
                section = comp.get("sectionName", "")

                # Use top-level price as a quick reference
                price = comp.get("price")
                old_price = comp.get("oldPrice")
                discount_pct = comp.get("displayDiscountPercentage")

                # Also check per-color prices for better discount info
                colors = comp.get("detail", {}).get("colors", [])
                for color in colors:
                    c_old = color.get("oldPrice")
                    c_pct = color.get("displayDiscountPercentage")
                    c_price = color.get("price")
                    if c_old and c_pct:
                        # Use the color variant with the highest discount
                        if discount_pct is None or c_pct > discount_pct:
                            price = c_price if c_price else price
                            old_price = c_old
                            discount_pct = c_pct

                if product_id is None or price is None:
                    continue

                products.append(
                    Product(
                        id=product_id,
                        name=name,
                        section=section,
                        category=category_name,
                        price=price,
                        old_price=old_price,
                        discount_pct=discount_pct,
                        url=_build_product_url(comp),
                        image_url=_extract_image_url(comp),
                    )
                )
    return products


async def fetch_products_for_category(
    client: httpx.AsyncClient, category_id: int, category_name: str
) -> list[Product]:
    """Fetch all products for a single category."""
    url = f"{config.BASE_URL}/category/{category_id}/products?ajax=true"
    try:
        resp = await client.get(url)
        resp.raise_for_status()
        data = resp.json()
        return _parse_products_from_response(data, category_name)
    except httpx.HTTPStatusError as exc:
        logger.warning(
            "HTTP {} for category {} ({})",
            exc.response.status_code,
            category_name,
            category_id,
        )
        return []
    except Exception as exc:
        logger.warning(
            "Error fetching category {} ({}): {}", category_name, category_id, exc
        )
        return []
