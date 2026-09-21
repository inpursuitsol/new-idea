from __future__ import annotations

from datetime import date

from pehli_salary.config import CHANNEL_URL, DISCLAIMER, TELEGRAM_TIP_WEEKDAYS
from pehli_salary.queue import QueueItem, load_queue
from pehli_salary.telegram_state import mark_tip, seen_tip


def is_tip_day(day: date) -> bool:
    return day.weekday() in TELEGRAM_TIP_WEEKDAYS


def next_tip_item() -> QueueItem | None:
    for item in load_queue():
        if item.kind == "short" and not seen_tip(item.id):
            return item
    return None


def format_tip(item: QueueItem) -> str:
    beats = item.beats[:2]
    lines = [
        "💰 TIP",
        "",
        item.title,
        "",
        item.hook,
    ]
    for beat in beats:
        lines.append(f"• {beat}")
    lines.extend(
        [
            "",
            f"👉 {item.cta}",
            "",
            "General education, personal advice nahi.",
            f"YouTube: {CHANNEL_URL}",
            "",
            "#PehliSalary #FirstJob #India",
        ]
    )
    return "\n".join(lines)


def post_due_tip(*, dry_run: bool = False) -> str | None:
    from datetime import datetime
    from zoneinfo import ZoneInfo

    from pehli_salary.config import IST
    from pehli_salary.queue import today_ist
    from pehli_salary.telegram_client import send_message

    day = today_ist(datetime.now(tz=ZoneInfo(IST)))
    if not is_tip_day(day):
        return None
    item = next_tip_item()
    if item is None:
        return None
    text = format_tip(item)
    send_message(text, dry_run=dry_run)
    if not dry_run:
        mark_tip(item.id)
    return item.id
