from __future__ import annotations

from datetime import date
from pathlib import Path

from pehli_salary.queue import QueueItem, load_queue
from pehli_salary.telegram_feeds import format_feed_post, parse_rss
from pehli_salary.telegram_state import load_state, mark_tip, seen_tip
from pehli_salary.telegram_tips import format_tip, is_tip_day


SAMPLE_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
<item>
<guid>job-1</guid>
<title>SSC CGL 2026</title>
<link>https://example.com/job</link>
<description><![CDATA[Apply online before 10 Oct.]]></description>
</item>
</channel>
</rss>
"""


def test_tip_day_schedule():
    assert is_tip_day(date(2026, 9, 22))  # Tue
    assert not is_tip_day(date(2026, 9, 21))  # Mon


def test_format_tip_contains_labels():
    item = load_queue()[0]
    text = format_tip(item)
    assert text.startswith("💰 TIP")
    assert item.title in text
    assert "personal advice nahi" in text


def test_parse_rss_extracts_job():
    entries = parse_rss(SAMPLE_RSS)
    assert len(entries) == 1
    assert entries[0].title == "SSC CGL 2026"
    assert entries[0].link == "https://example.com/job"
    assert entries[0].entry_id == "https://example.com/job"


def test_title_key_dedupes_same_job_with_new_link(tmp_path: Path, monkeypatch):
    from pehli_salary.telegram_feeds import FeedEntry, mark_entry, poll_feeds, seen_entry

    state_path = tmp_path / "posted.json"
    monkeypatch.setattr("pehli_salary.config.TELEGRAM_STATE_PATH", state_path)

    entry = FeedEntry(
        "https://example.com/job?v=1",
        "SSC CGL 2026",
        "https://example.com/job?v=1",
        "Apply online",
        "📢 JOB",
    )
    mark_entry(entry)
    assert seen_entry(
        FeedEntry(
            "https://example.com/job?v=2",
            "SSC CGL 2026",
            "https://example.com/job?v=2",
            "Apply online",
            "📢 JOB",
        )
    )


def test_poll_skips_already_posted_link(tmp_path: Path, monkeypatch):
    from pehli_salary.telegram_feeds import FeedEntry, poll_feeds

    state_path = tmp_path / "posted.json"
    entry = FeedEntry(
        "https://example.com/job",
        "SSC CGL 2026",
        "https://example.com/job",
        "Apply online",
        "📢 JOB",
    )

    class FakeResponse:
        def read(self):
            return SAMPLE_RSS.encode()

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    monkeypatch.setattr(
        "pehli_salary.telegram_feeds.load_sources",
        lambda: [{"label": "📢 JOB", "url": "https://example.com/feed"}],
    )
    monkeypatch.setattr("pehli_salary.telegram_feeds.fetch_feed", lambda url: SAMPLE_RSS)
    monkeypatch.setattr("pehli_salary.config.TELEGRAM_STATE_PATH", state_path)
    sent: list[str] = []
    monkeypatch.setattr(
        "pehli_salary.telegram_client.send_message",
        lambda text, dry_run=False: sent.append(text) or {},
    )

    first = poll_feeds(dry_run=False, limit_per_feed=1)
    second = poll_feeds(dry_run=False, limit_per_feed=1)
    assert len(first) == 1
    assert second == []
    assert len(sent) == 1


def test_format_feed_post_has_verify_line():
    from pehli_salary.telegram_feeds import FeedEntry

    text = format_feed_post(
        FeedEntry("1", "SSC", "https://example.com", "Apply now", "📢 JOB"),
        "📢 JOB",
    )
    assert "📢 JOB" in text
    assert "verify" in text.lower()


def test_tip_state_tracks_posts(tmp_path: Path):
    state_path = tmp_path / "posted.json"
    mark_tip("s001", path=state_path)
    assert seen_tip("s001", path=state_path)
    assert load_state(state_path)["tips"] == ["s001"]


def test_post_due_tip_skips_non_tip_day(monkeypatch):
    from datetime import date

    from pehli_salary.telegram_tips import post_due_tip

    monkeypatch.setattr("pehli_salary.queue.today_ist", lambda _now=None: date(2026, 9, 21))
    assert post_due_tip(dry_run=True) is None


def test_format_tip_short_item():
    item = QueueItem(
        id="x",
        kind="short",
        publish_on=date(2026, 1, 1),
        title="Test title",
        hook="Hook line.",
        beats=["Beat one."],
        cta="Comment.",
        tags=[],
    )
    text = format_tip(item)
    assert "Test title" in text
    assert "Beat one." in text
