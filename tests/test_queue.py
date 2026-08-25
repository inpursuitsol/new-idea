from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

from pehli_salary.copy import description_for, validate_title
from pehli_salary.queue import QueueItem, items_for_day, load_queue, today_ist


def test_queue_has_unique_ids_and_titles():
    items = load_queue()
    assert items
    ids = [i.id for i in items]
    assert len(ids) == len(set(ids))
    titles = [i.title for i in items]
    assert len(titles) == len(set(titles))


def test_short_titles_fit_youtube():
    for item in load_queue():
        title = validate_title(item.title)
        assert 8 <= len(title) <= 100
        assert "game-changer" not in title.lower()
        assert "let's dive" not in title.lower()


def test_descriptions_carry_disclaimer_and_human_hook():
    item = load_queue()[0]
    text = description_for(item)
    assert "personal advice nahi" in text
    assert item.hook in text
    assert "#" in text


def test_schedule_slots_are_ist_prime_time():
    short = next(i for i in load_queue() if i.kind == "short")
    longform = next(i for i in load_queue() if i.kind == "longform")
    assert short.publish_at().strftime("%H:%M") == "19:30"
    assert longform.publish_at().strftime("%H:%M") == "10:00"
    assert str(short.publish_at().tzinfo) == "Asia/Kolkata"


def test_due_lookup_by_calendar_day():
    day = date(2026, 8, 27)
    due = items_for_day(day)
    assert [i.id for i in due] == ["s001"]
    assert items_for_day(date(2026, 8, 26)) == []


def test_today_ist_converts_utc():
    utc = datetime(2026, 8, 27, 3, 0, tzinfo=ZoneInfo("UTC"))
    assert today_ist(utc) == date(2026, 8, 27)


def test_caption_chunks_are_short():
    item = load_queue()[0]
    chunks = item.caption_chunks()
    assert chunks
    assert all(len(c.split()) <= 6 for c in chunks)


def test_future_private_upload_gets_publish_at():
    from pehli_salary.youtube_client import build_status

    item = load_queue()[0]
    future = datetime(2026, 8, 27, 10, 0, tzinfo=ZoneInfo("UTC"))
    status = build_status(item, privacy="private", now=future)
    assert status["privacyStatus"] == "private"
    assert status["publishAt"].startswith("2026-08-27T")


def test_past_slot_goes_public():
    from pehli_salary.youtube_client import build_status

    item = load_queue()[0]
    past = datetime(2026, 8, 28, tzinfo=ZoneInfo("UTC"))
    status = build_status(item, privacy="private", now=past)
    assert status["privacyStatus"] == "public"
    assert "publishAt" not in status


def test_queue_item_narration_is_spoken():
    item = QueueItem(
        id="x",
        kind="short",
        publish_on=date(2026, 1, 1),
        title="t",
        hook="Hook one.",
        beats=["Beat two."],
        cta="Subscribe.",
        tags=["a"],
    )
    assert item.narration() == "Hook one. Beat two. Subscribe."
