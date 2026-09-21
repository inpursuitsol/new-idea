from __future__ import annotations

import re
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

import yaml

from pehli_salary.config import TELEGRAM_SOURCES_PATH
from pehli_salary.telegram_state import mark_feed, seen_feed


@dataclass(frozen=True)
class FeedEntry:
    entry_id: str
    title: str
    link: str
    summary: str
    label: str


def load_sources(path: Path = TELEGRAM_SOURCES_PATH) -> list[dict]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return list(raw.get("feeds") or [])


def fetch_feed(url: str, *, timeout: int = 30) -> str:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "Contentlovers108TelegramBot/1.0"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


def parse_rss(xml_text: str) -> list[FeedEntry]:
    root = ET.fromstring(xml_text)
    channel = root.find("channel")
    if channel is None:
        channel = root
    entries: list[FeedEntry] = []
    for item in channel.findall("item"):
        title = _text(item.find("title"))
        link = _text(item.find("link"))
        link = link.strip()
        guid = _text(item.find("guid")) or link or title
        summary = _clean_html(_text(item.find("description")))
        if title and link:
            entries.append(
                FeedEntry(
                    entry_id=_entry_id(link, guid),
                    title=title.strip(),
                    link=link.strip(),
                    summary=summary.strip(),
                    label="",
                )
            )
    return entries


def format_feed_post(entry: FeedEntry, label: str) -> str:
    summary = entry.summary
    if len(summary) > 280:
        summary = summary[:277].rstrip() + "..."
    return "\n".join(
        [
            label,
            "",
            entry.title,
            "",
            summary,
            "",
            f"🔗 {entry.link}",
            "",
            "Aggregator link — official notification par verify karo.",
        ]
    )


def poll_feeds(*, dry_run: bool = False, limit_per_feed: int = 1) -> list[str]:
    from pehli_salary.telegram_client import send_message

    posted: list[str] = []
    for source in load_sources():
        label = str(source.get("label") or "📢 ALERT")
        url = str(source["url"])
        entries = parse_rss(fetch_feed(url))
        count = 0
        for entry in entries:
            if count >= limit_per_feed:
                break
            if seen_feed(entry.entry_id):
                continue
            text = format_feed_post(
                FeedEntry(
                    entry_id=entry.entry_id,
                    title=entry.title,
                    link=entry.link,
                    summary=entry.summary,
                    label=label,
                ),
                label,
            )
            send_message(text, dry_run=dry_run)
            if not dry_run:
                mark_feed(entry.entry_id)
            posted.append(entry.entry_id)
            count += 1
    return posted


def _text(node: ET.Element | None) -> str:
    if node is None or node.text is None:
        return ""
    return node.text


def _clean_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text).replace("\n", " ").strip()


def _entry_id(link: str, guid: str) -> str:
    """Stable dedup key across RSS runs (link beats guid)."""
    normalized = link.strip().rstrip("/")
    return normalized or guid.strip()
