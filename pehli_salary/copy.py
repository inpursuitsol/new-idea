from __future__ import annotations

from pehli_salary.config import CHANNEL_HASHTAGS, DISCLAIMER
from pehli_salary.queue import QueueItem


def description_for(item: QueueItem) -> str:
    lines = [
        item.hook,
        "",
        *item.beats,
        "",
        item.cta,
        "",
        DISCLAIMER,
        "",
        CHANNEL_HASHTAGS,
    ]
    return "\n".join(lines)


def youtube_tags(item: QueueItem) -> list[str]:
    base = ["pehli salary club", "Indian salary", "Hinglish finance", "first job India"]
    merged = []
    seen = set()
    for tag in [*item.tags, *base]:
        key = tag.lower()
        if key not in seen:
            seen.add(key)
            merged.append(tag)
    return merged[:12]


def validate_title(title: str) -> str:
    title = title.strip()
    if not title:
        raise ValueError("title required")
    if len(title) > 100:
        return title[:97] + "..."
    return title
