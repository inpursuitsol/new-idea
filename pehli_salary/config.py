from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHANNEL_DIR = ROOT / "channel"
QUEUE_PATH = CHANNEL_DIR / "queue.yaml"
BRAND_PATH = CHANNEL_DIR / "brand.yaml"
TELEGRAM_SOURCES_PATH = CHANNEL_DIR / "telegram_sources.yaml"
OUTBOX = ROOT / "outbox"
TELEGRAM_STATE_PATH = ROOT / ".telegram" / "posted.json"
IST = "Asia/Kolkata"
TELEGRAM_CHANNEL_ID = "@contentlovers108"
TELEGRAM_TIP_WEEKDAYS = {1, 3, 5}  # Tue, Thu, Sat
TELEGRAM_TIP_HOUR = 11
TELEGRAM_TIP_MINUTE = 11  # 11:11 IST — matches first Short slot in queue.yaml
YOUTUBE_CATEGORY_EDUCATION = "27"
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
DISCLAIMER = (
    "Yeh video general education hai, personal advice nahi. "
    "Tax/PF ke final decision ke liye apna CA / employer HR dekho."
)
CHANNEL_HANDLE = "@Contentlovers108"
CHANNEL_URL = "https://www.youtube.com/@Contentlovers108"
