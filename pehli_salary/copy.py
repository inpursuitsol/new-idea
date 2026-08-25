from __future__ import annotations

from pehli_salary.config import CHANNEL_HANDLE, DISCLAIMER
from pehli_salary.queue import QueueItem


def description_for(item: QueueItem) -> str:
    # Looks like a person typed this in Studio, not a template dump.
    lines = [
        item.hook.rstrip("."),
        "",
        "jo maine khud pehli naukri mein miss kiya, wahi hai.",
        "",
        *item.beats,
        "",
        item.cta,
        "",
        "agar tumhara number alag hai (city, rent, company), comment mein likh dena. next wale mein use karunga.",
        "",
        f"{CHANNEL_HANDLE} · pehli naukri wala series, poora finance TV nahi.",
        "",
        DISCLAIMER,
    ]
    return "\n".join(lines)


def youtube_tags(item: QueueItem) -> list[str]:
    base = ["pehli salary", "first job India", "in hand salary"]
    merged = []
    seen = set()
    for tag in [*item.tags, *base]:
        key = tag.lower()
        if key not in seen:
            seen.add(key)
            merged.append(tag)
    return merged[:8]


def validate_title(title: str) -> str:
    title = title.strip()
    if not title:
        raise ValueError("title required")
    if len(title) > 100:
        return title[:97] + "..."
    return title
