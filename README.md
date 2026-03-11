# zara

A discount monitor for [Zara Japan](https://www.zara.com/jp/). Scans all product categories and reports items on sale that meet a configurable discount threshold.

## Features

- Fetches all product categories and items from Zara JP's internal API
- **Concurrent fetching**: scans multiple categories in parallel (configurable concurrency)
- Real-time output: prints matching deals as soon as they are found
- Configurable discount threshold (e.g. only show items >= 30% off)
- Telegram notifications for matching deals (optional)
- Designed for crontab: runs once and exits, no resident process needed

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
| `ZARA_REQUEST_TIMEOUT` | `30` | HTTP request timeout in seconds |
| `ZARA_REQUEST_DELAY` | `0.5` | Delay between requests in seconds |
| `ZARA_CONCURRENCY` | `10` | Max concurrent category fetches |
| `ZARA_TG_BOT_TOKEN` | *(empty)* | Telegram bot token (leave empty to disable) |
| `ZARA_TG_CHAT_ID` | *(empty)* | Telegram chat ID to send notifications to |

## Usage

### Run a scan

```bash
uv run zara
```

### Custom threshold

```bash
uv run zara --threshold 50
```

### Verbose output

```bash
uv run zara -v
```

### Custom concurrency

```bash
uv run zara --concurrency 20
```

### Scheduled daily scan via crontab

The recommended way to run daily scans is via system crontab. This avoids keeping a process resident in memory.

```bash
crontab -e
```

Add the following line to run at 7:20 AM JST every day:

```cron
20 7 * * * cd /path/to/zara && /path/to/.venv/bin/zara >> /path/to/zara/scan.log 2>&1
```

For example, if the project is at `/root/code/zara`:

```cron
20 7 * * * cd /root/code/zara && /root/code/zara/.venv/bin/zara >> /root/code/zara/scan.log 2>&1
```

> **Tip**: Make sure the server timezone is set to `Asia/Tokyo` (JST), or adjust the cron schedule accordingly. Check with `timedatectl` or `date`.

To verify the crontab is installed:

```bash
crontab -l
```

## Output

- Regular log messages are printed at `INFO` level
- Items matching the discount threshold are highlighted with `SUCCESS` (green) via [loguru](https://github.com/Delgan/loguru)

Example:

```
2026-03-09 15:26:08 | INFO     | Starting Zara JP discount scan (threshold: >= 50% off, concurrency: 10)
2026-03-09 15:26:08 | INFO     | Found 746 product categories to scan
2026-03-09 15:26:10 | SUCCESS  | [WOMAN] ソフトオーバーサイズコート | ¥6,590 (was ¥13,590, -51% off) | https://www.zara.com/jp/ja/...
2026-03-09 15:26:48 | INFO     | Scan complete in 40s. 12345 unique products scanned, 42 items matched threshold (>= 50% off)
```

## Telegram Notifications

To enable Telegram notifications, set `ZARA_TG_BOT_TOKEN` and `ZARA_TG_CHAT_ID` in `.env`:

1. Create a bot via [@BotFather](https://t.me/BotFather) and copy the token
2. Get your chat ID by sending a message to the bot and visiting `https://api.telegram.org/bot<TOKEN>/getUpdates`
3. Fill in both values in `.env`

When enabled, each matching deal is sent as an individual message in real-time, followed by a summary when the scan completes. Leave both values empty to disable.

## License

MIT
