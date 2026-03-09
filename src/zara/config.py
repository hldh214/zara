from pathlib import Path

from dotenv import load_dotenv

import os

# Load .env file from project root
_env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(_env_path)

# Discount threshold in percentage (e.g. 30 means items with >= 30% off will be reported)
DISCOUNT_THRESHOLD = int(os.environ.get("ZARA_DISCOUNT_THRESHOLD", "30"))

# Zara JP API base URL
BASE_URL = os.environ.get("ZARA_BASE_URL", "https://www.zara.com/jp/ja")

# Scheduler settings (JST)
SCHEDULE_HOUR = int(os.environ.get("ZARA_SCHEDULE_HOUR", "7"))
SCHEDULE_MINUTE = int(os.environ.get("ZARA_SCHEDULE_MINUTE", "20"))

# Timezone
TIMEZONE = os.environ.get("ZARA_TIMEZONE", "Asia/Tokyo")

# HTTP request settings
REQUEST_TIMEOUT = int(os.environ.get("ZARA_REQUEST_TIMEOUT", "30"))
REQUEST_DELAY = float(os.environ.get("ZARA_REQUEST_DELAY", "0.5"))

# Product listing layouts that contain actual products
PRODUCT_LAYOUTS = {"products-category-view", "origins-products-category-view"}
