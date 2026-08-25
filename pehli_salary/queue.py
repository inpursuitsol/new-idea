from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

from pehli_salary.config import IST, QUEUE_PATH

IST_TZ = ZoneInfo(IST)


@dataclass(frozen=True)
class QueueItem:
    id: str
    kind: str
    publish_on: date
    title: str
    hook: str
    beats: list[str]
    cta: str
    tags: list[str]
    spoken: str | None = None
    captions: list[str] | None = None
    publish_time: time | None = None

    @property
    def slot_time(self) -> time:
        if self.publish_time is not None:
            return self.publish_time
        if self.kind == "longform":
            return time(10, 0)
        return time(19, 30)

    def publish_at(self) -> datetime:
        return datetime.combine(self.publish_on, self.slot_time, tzinfo=IST_TZ)

    def narration(self) -> str:
        if self.spoken and self.spoken.strip():
            return " ".join(self.spoken.split())
        parts = [self.hook, *self.beats, self.cta]
        return " ".join(part.strip() for part in parts)

    def caption_chunks(self) -> list[str]:
        if self.captions:
            return [c.strip() for c in self.captions if c and c.strip()]
        chunks: list[str] = []
        for block in (self.hook, *self.beats, self.cta):
            chunks.extend(_split_caption(block))
        return chunks or [self.title]


def _parse_clock(value) -> time | None:
    if not value:
        return None
    hour, minute = str(value).strip().split(":")
    return time(int(hour), int(minute))


def _split_caption(text: str, max_words: int = 4) -> list[str]:
    words = text.split()
    if not words:
        return []
    return [" ".join(words[i : i + max_words]) for i in range(0, len(words), max_words)]


def load_queue(path=QUEUE_PATH) -> list[QueueItem]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    items = []
    for row in raw["items"]:
        items.append(
            QueueItem(
                id=row["id"],
                kind=row["kind"],
                publish_on=date.fromisoformat(str(row["publish_on"])),
                title=row["title"],
                hook=row["hook"],
                beats=list(row["beats"]),
                cta=row["cta"],
                tags=list(row.get("tags") or []),
                spoken=row.get("spoken"),
                captions=list(row["captions"]) if row.get("captions") else None,
                publish_time=_parse_clock(row.get("publish_time")),
            )
        )
    return items


def items_for_day(day: date, items: list[QueueItem] | None = None) -> list[QueueItem]:
    items = items if items is not None else load_queue()
    return [item for item in items if item.publish_on == day]


def today_ist(now: datetime | None = None) -> date:
    current = now or datetime.now(tz=IST_TZ)
    if current.tzinfo is None:
        current = current.replace(tzinfo=IST_TZ)
    return current.astimezone(IST_TZ).date()


def voiceover_path(item: QueueItem) -> Path | None:
    from pehli_salary.config import CHANNEL_DIR

    for ext in (".mp3", ".m4a", ".wav"):
        candidate = CHANNEL_DIR / "voiceovers" / f"{item.id}{ext}"
        if candidate.exists():
            return candidate
    return None
