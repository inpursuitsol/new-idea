from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHANNEL_DIR = ROOT / "channel"
QUEUE_PATH = CHANNEL_DIR / "queue.yaml"
BRAND_PATH = CHANNEL_DIR / "brand.yaml"
OUTBOX = ROOT / "outbox"
IST = "Asia/Kolkata"
YOUTUBE_CATEGORY_EDUCATION = "27"
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
DISCLAIMER = (
    "Yeh video general education hai, personal advice nahi. "
    "Tax/PF ke final decision ke liye apna CA / employer HR dekho."
)
CHANNEL_HANDLE = "@Contentlovers108"
CHANNEL_URL = "https://www.youtube.com/@Contentlovers108"
