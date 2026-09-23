from __future__ import annotations

from datetime import date

from pehli_salary.jobs_promote import promote
from pehli_salary.site_jobs import GrowthConfig, SiteJob


def _config() -> GrowthConfig:
    return GrowthConfig(
        site="https://inpursuit.co.in",
        jobs_api="https://inpursuit.co.in/wp-json/wp/v2/job",
        hub_url="https://inpursuit.co.in/jobs/",
        indexnow_key="abc123key",
        utm_source="telegram",
        utm_medium="social",
        utm_campaign="inpursuit-jobs",
        promote_limit=2,
    )


def _jobs() -> list[SiteJob]:
    return [
        SiteJob("75", "a", "Role A", "https://inpursuit.co.in/jobs/a/", "2026-09-18", "Summary A", "Bangalore"),
        SiteJob("74", "b", "Role B", "https://inpursuit.co.in/jobs/b/", "2026-09-17", "Summary B", ""),
        SiteJob("73", "c", "Role C", "https://inpursuit.co.in/jobs/c/", "2026-09-16", "Summary C", "Hyderabad"),
    ]


def test_promote_posts_newest_roles_and_dedupes(tmp_path, monkeypatch):
    sent: list[str] = []
    monkeypatch.setattr(
        "pehli_salary.jobs_promote.submit_indexnow",
        lambda urls, config, dry_run=False: {"status": "ok", "count": len(urls)},
    )
    monkeypatch.setattr(
        "pehli_salary.jobs_promote.notify_google_indexing",
        lambda urls, dry_run=False: {"status": "skipped"},
    )
    state = tmp_path / "jobs_promoted.json"

    def _send(text, dry_run=False):
        sent.append(text)
        return {}

    first = promote(
        dry_run=False,
        today=date(2026, 9, 23),  # Wednesday, no digest
        config=_config(),
        state_path=state,
        jobs=_jobs(),
        send=_send,
    )
    second = promote(
        dry_run=False,
        today=date(2026, 9, 23),
        config=_config(),
        state_path=state,
        jobs=_jobs(),
        send=_send,
    )
    third = promote(
        dry_run=False,
        today=date(2026, 9, 23),
        config=_config(),
        state_path=state,
        jobs=_jobs(),
        send=_send,
    )
    assert first["posted"] == [
        "https://inpursuit.co.in/jobs/a/",
        "https://inpursuit.co.in/jobs/b/",
    ]
    assert first["digest"] is False
    assert second["posted"] == ["https://inpursuit.co.in/jobs/c/"]
    assert third["posted"] == []
    assert len(sent) == 3
    assert "inpursuit.co.in/jobs/" in sent[0]


def test_promote_digest_on_monday_links_hub(monkeypatch):
    sent: list[str] = []
    monkeypatch.setattr(
        "pehli_salary.jobs_promote.submit_indexnow",
        lambda urls, config, dry_run=False: {"status": "dry_run", "count": len(urls)},
    )
    monkeypatch.setattr(
        "pehli_salary.jobs_promote.notify_google_indexing",
        lambda urls, dry_run=False: {"status": "skipped"},
    )

    result = promote(
        dry_run=True,
        limit=0,
        today=date(2026, 9, 21),  # Monday
        config=_config(),
        state_path=None,
        jobs=_jobs(),
        send=lambda text, dry_run=False: sent.append(text),
    )
    assert result["posted"] == []
    assert result["digest"] is True
    assert "inpursuit.co.in/jobs" in sent[0]
    assert "Role A" in sent[0]
    assert "utm_campaign=inpursuit-jobs-hub" in sent[0]


def test_google_indexing_skips_without_credentials(monkeypatch):
    from pehli_salary.jobs_promote import notify_google_indexing

    monkeypatch.delenv("GOOGLE_INDEXING_SA_JSON", raising=False)
    assert notify_google_indexing(["https://inpursuit.co.in/jobs/"], dry_run=False)["status"] == "skipped"
