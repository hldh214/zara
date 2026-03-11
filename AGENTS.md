# AGENTS.md

## Project Overview

Zara JP discount monitor. Scans all product categories on zara.com/jp via their internal JSON API, detects sale items meeting a configurable discount threshold, and sends Telegram notifications with product photos.

- **Language:** Python 3.12+
- **Package manager:** uv (not pip/poetry)
- **Build backend:** hatchling (src layout: `src/zara/`)
- **HTTP client:** httpx (async)
- **Logging:** loguru
- **Config:** python-dotenv + `.env`
- **Scheduling:** system crontab (no in-process scheduler)

## Build / Run Commands

```bash
# Install dependencies
uv sync

# Run a single scan
uv run zara

# Run with custom threshold and concurrency
uv run zara --threshold 50 --concurrency 20

# Import check (no test suite exists yet)
uv run python -c "from zara.cli import main"
```

There are **no tests, no linter config, no type checker config, no CI/CD** in this repo. Validate changes by running `uv run python -c "from zara.cli import main"` to confirm imports, and optionally `uv run zara --threshold 99` for a quick live smoke test.

## Code Style

### Imports

Every module (except `config.py`) starts with `from __future__ import annotations`.

Import order with **one blank line** between each group:
1. `from __future__ import annotations`
2. stdlib (`import asyncio`, `from dataclasses import dataclass`)
3. Third-party (`import httpx`, `from loguru import logger`)
4. Local (`from zara import config`, `from zara.client import Product`)

Multi-name imports use parenthesized format with trailing comma, one name per line:
```python
from zara.client import (
    Product,
    fetch_categories,
    get_product_category_ids,
    HEADERS,
)
```

Config is always imported as the module, never individual values (so CLI overrides propagate):
```python
# Correct — reads value at runtime
from zara import config
threshold = config.DISCOUNT_THRESHOLD

# Wrong — copies value at import time, ignores CLI overrides
from zara.config import DISCOUNT_THRESHOLD
```

### Type Annotations

All function parameters and return types must be annotated. Use modern Python 3.10+ syntax (enabled by `from __future__ import annotations`):
- `list[dict]` not `List[Dict]`
- `tuple[int, str]` not `Tuple[int, str]`
- `int | None` not `Optional[int]`
- `set[int]` not `Set[int]`

Local variables may have inline type annotations when it aids clarity: `seen: set[int] = set()`.

### Naming Conventions

| Kind                | Convention           | Example                       |
|---------------------|----------------------|-------------------------------|
| Functions           | `snake_case`         | `run_scan`, `fetch_categories`|
| Private functions   | `_leading_underscore`| `_fetch_one`, `_build_url`    |
| Constants           | `UPPER_SNAKE_CASE`   | `HEADERS`, `BASE_URL`         |
| Private constants   | `_UPPER_SNAKE_CASE`  | `_IMAGE_WIDTH`, `_TG_API`     |
| Classes             | `PascalCase`         | `Product`                     |
| Variables           | `snake_case`         | `cat_id`, `total_hits`        |
| Exception variable  | `exc`                | never `e` or `err`            |
| Short loop vars     | OK in tight loops    | `p`, `m`, `comp`, `cat`       |

### Formatting

- Line length: keep under ~110 characters.
- Use parentheses for line continuation, never backslash `\`.
- Two blank lines between top-level definitions (functions, classes).
- No trailing whitespace. Empty lines must be truly empty (no spaces).

### Docstrings

Imperative mood, starts with a verb, ends with a period. Single-line when short:
```python
def fetch_categories(client: httpx.AsyncClient) -> list[dict]:
    """Fetch the full category tree from Zara JP."""
```

Multi-line: summary on first `"""` line, blank line, body, closing `"""` on its own line. Use RST-style double backticks for inline code:
```python
def _extract_image_url(comp: dict) -> str:
    """Extract the primary product image URL from the first color's xmedia.

    Prefers ``kind == "full"`` (the hero shot); falls back to the first
    xmedia entry.
    """
```

Not every trivial helper needs a docstring (e.g. `_is_enabled`), but all public functions should have one.

### Logging

Use **loguru** exclusively. Never use stdlib `logging`.

Always use loguru `{}` placeholders — **never** f-strings inside log calls:
```python
# Correct
logger.info("Found {} categories", len(cat_ids))
logger.success("[{}] {} | ¥{:,} (was ¥{:,})", section, name, price, old_price)

# Wrong
logger.info(f"Found {len(cat_ids)} categories")
```

Levels used in this project:
- `logger.info()` — normal progress
- `logger.success()` — items matching discount threshold (renders green)
- `logger.warning()` — non-fatal errors (HTTP failures, Telegram errors)
- `logger.debug()` — verbose detail (enabled with `--verbose`)

### Error Handling

- Catch specific exceptions before broad `Exception`.
- Name the exception variable `exc`.
- Use `logger.warning()` for non-fatal errors. Never `logger.error()` in current codebase.
- Return empty collections (`[]`) on failure rather than raising — the scan must continue.
- Early-return guard clauses for preconditions: `if not _is_enabled(): return`.

```python
try:
    resp = await client.get(url)
    resp.raise_for_status()
except httpx.HTTPStatusError as exc:
    logger.warning("HTTP {} for {}", exc.response.status_code, name)
    return []
except Exception as exc:
    logger.warning("Error fetching {}: {}", name, exc)
    return []
```

### Async Patterns

All HTTP I/O is async. Entry point uses `asyncio.run()` from sync CLI code.

- Shared `httpx.AsyncClient` passed as a parameter for scanning operations.
- Concurrency bounded by `asyncio.Semaphore` + `asyncio.create_task` + `asyncio.as_completed`.
- Rate limiting via `asyncio.sleep()` inside the semaphore block.
- Telegram notifications create a new `httpx.AsyncClient` per call.

### Data Access

Defensive `.get()` with defaults for all JSON/dict access:
```python
node.get("layout", "")
comp.get("detail", {}).get("colors", [])
```

### Configuration

All settings live in `config.py` as mutable module-level variables read from env vars via `os.environ.get()`. CLI may override values by direct assignment (`config.DISCOUNT_THRESHOLD = args.threshold`).

### Comments

- Always write comments in English, even though the project deals with Japanese product data.
- Use inline `#` comments. Keep them brief.

### Database / Secrets

- Never use foreign keys or cascades in any RDBMS (not currently applicable but noted for future).
- Never commit `.env` or files containing secrets. The `.env` file is gitignored.
- Never reset or wipe any database. Roll back modified parts if possible, or ask the user.

### Git

- Do not commit changes automatically. Always ask the user first.
- Do not push unless explicitly asked.

### Dependencies

- Always use `uv` for package management. Never `pip install` directly.
- HTTP: `httpx` (async). No `requests` or `aiohttp`.
- Logging: `loguru`. No stdlib `logging`.
- Config: `python-dotenv`. No Pydantic settings.
- Data classes: stdlib `@dataclass`. No Pydantic models, no attrs.
