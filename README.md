# zara

A discount monitor for [Zara Japan](https://www.zara.com/jp/). Scans all product categories and reports items on sale that meet a configurable discount threshold.

## Features

- Fetches all product categories and items from Zara JP's internal API
- Real-time output: prints matching deals as soon as they are found
- Configurable discount threshold (e.g. only show items >= 30% off)
- Built-in scheduler for daily automated scans (default: 7:20 AM JST)
- Single-run mode for one-off checks

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)

## Setup

```bash
# Install dependencies
uv sync

# Copy the example config and edit as needed
cp .env.example .env
```

## Configuration

All settings are configured via environment variables in `.env`:

| Variable | Default | Description |
|---|---|---|
| `ZARA_DISCOUNT_THRESHOLD` | `30` | Minimum discount % to report |
| `ZARA_BASE_URL` | `https://www.zara.com/jp/ja` | Zara API base URL |
| `ZARA_SCHEDULE_HOUR` | `7` | Scheduler hour (24h) |
| `ZARA_SCHEDULE_MINUTE` | `20` | Scheduler minute |
| `ZARA_TIMEZONE` | `Asia/Tokyo` | Timezone for scheduler |
| `ZARA_REQUEST_TIMEOUT` | `30` | HTTP request timeout in seconds |
| `ZARA_REQUEST_DELAY` | `0.5` | Delay between requests in seconds |

## Usage

### Single scan

```bash
uv run zara --once
```

### Single scan with custom threshold

```bash
uv run zara --once --threshold 50
```

### Run as a daily scheduler

```bash
uv run zara
```

This starts a blocking scheduler that runs a scan daily at the configured time (default 7:20 AM JST).

### Verbose output

```bash
uv run zara --once -v
```

## Output

- Regular log messages are printed at `INFO` level
- Items matching the discount threshold are highlighted with `SUCCESS` (green) via [loguru](https://github.com/Delgan/loguru)

Example:

```
2026-03-09 15:26:08 | INFO     | Starting Zara JP discount scan (threshold: >= 50% off)
2026-03-09 15:26:08 | INFO     | Found 746 product categories to scan
2026-03-09 15:26:10 | SUCCESS  | [WOMAN] ソフトオーバーサイズコート | ¥6,590 (was ¥13,590, -51% off) | https://www.zara.com/jp/ja/...
```

## License

MIT
