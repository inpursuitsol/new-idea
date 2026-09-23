"""Share inpursuit.co.in jobs and notify search engines when they change."""

from __future__ import annotations

import json
import os
from datetime import date
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request

from pehli_salary.config import JOBS_PROMOTED_PATH
from pehli_salary.site_jobs import (
    USER_AGENT,
    GrowthConfig,
    SiteJob,
    fetch_jobs,
    fetch_text,
    format_digest,
    format_job_post,
    indexnow_payload,
    load_growth_config,
)

DIGEST_WEEKDAYS = {0, 3}  # Monday, Thursday


def load_promoted(path: Path | None = None) -> dict[str, list[str]]:
    state_path = path or JOBS_PROMOTED_PATH
    if not state_path.exists():
        return {"promoted": [], "digests": [], "indexed": []}
    raw = json.loads(state_path.read_text(encoding="utf-8"))
    return {
        "promoted": list(raw.get("promoted") or []),
        "digests": list(raw.get("digests") or []),
        "indexed": list(raw.get("indexed") or []),
    }


def save_promoted(state: dict[str, list[str]], path: Path | None = None) -> None:
    state_path = path or JOBS_PROMOTED_PATH
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _index_key(job: SiteJob) -> str:
    return f"{job.link}|{job.modified}"


def _key_is_live(config: GrowthConfig) -> bool:
    try:
        body, _headers = fetch_text(config.indexnow_key_location)
    except (HTTPError, URLError, TimeoutError, OSError):
        return False
    return body.strip() == config.indexnow_key


def submit_indexnow(urls: list[str], config: GrowthConfig, *, dry_run: bool) -> dict:
    if not urls:
        return {"status": "skipped", "reason": "no urls"}
    payload = indexnow_payload(urls, config)
    if dry_run:
        return {"status": "dry_run", "count": len(payload["urlList"])}
    if not _key_is_live(config):
        return {
            "status": "skipped",
            "reason": f"Upload {config.indexnow_key}.txt to the site root before IndexNow will accept pings.",
        }
    request = Request(
        "https://api.indexnow.org/indexnow",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8", "User-Agent": USER_AGENT},
        method="POST",
    )
    try:
        import urllib.request

        with urllib.request.urlopen(request, timeout=30) as response:
            return {"status": "ok", "http": response.status, "count": len(payload["urlList"])}
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:300]
        return {"status": "error", "http": exc.code, "detail": detail}
    except (URLError, TimeoutError, OSError) as exc:
        return {"status": "error", "detail": str(exc)}


def notify_google_indexing(urls: list[str], *, dry_run: bool) -> dict:
    raw = os.environ.get("GOOGLE_INDEXING_SA_JSON", "").strip()
    if not raw:
        return {"status": "skipped", "reason": "GOOGLE_INDEXING_SA_JSON not set"}
    if not urls:
        return {"status": "skipped", "reason": "no urls"}
    if dry_run:
        return {"status": "dry_run", "count": len(urls)}
    try:
        info = json.loads(raw)
        from google.oauth2 import service_account
        from googleapiclient.discovery import build

        credentials = service_account.Credentials.from_service_account_info(
            info,
            scopes=["https://www.googleapis.com/auth/indexing"],
        )
        service = build("indexing", "v3", credentials=credentials, cache_discovery=False)
        notified: list[str] = []
        for url in urls:
            service.urlNotifications().publish(body={"url": url, "type": "URL_UPDATED"}).execute()
            notified.append(url)
        return {"status": "ok", "count": len(notified)}
    except Exception as exc:  # noqa: BLE001 — report and keep the Telegram posts
        return {"status": "error", "detail": str(exc)[:300]}


def promote(
    *,
    dry_run: bool = False,
    limit: int | None = None,
    today: date | None = None,
    config: GrowthConfig | None = None,
    state_path: Path | None = None,
    jobs: list[SiteJob] | None = None,
    send=None,
) -> dict:
    from pehli_salary.queue import today_ist
    from pehli_salary.telegram_client import send_message

    growth = config or load_growth_config()
    day = today or today_ist()
    state = load_promoted(state_path)
    roster = jobs if jobs is not None else fetch_jobs(growth)
    cap = growth.promote_limit if limit is None else limit
    sender = send or send_message

    fresh = [job for job in roster if job.job_id and job.job_id not in state["promoted"]]
    posted: list[str] = []
    messages: list[str] = []
    for job in fresh[: max(cap, 0)]:
        text = format_job_post(job, growth)
        messages.append(text)
        sender(text, dry_run=dry_run)
        posted.append(job.link)
        if not dry_run:
            state["promoted"].append(job.job_id)

    digest_id = day.isoformat()
    digest_posted = False
    if roster and day.weekday() in DIGEST_WEEKDAYS and digest_id not in state["digests"]:
        text = format_digest(roster, growth)
        messages.append(text)
        sender(text, dry_run=dry_run)
        digest_posted = True
        if not dry_run:
            state["digests"].append(digest_id)

    changed = [job for job in roster if _index_key(job) not in state["indexed"]]
    urls = [growth.hub_url] if changed else []
    urls.extend(job.link for job in changed)
    indexnow = submit_indexnow(urls, growth, dry_run=dry_run)
    google = notify_google_indexing(urls, dry_run=dry_run)
    if not dry_run and indexnow.get("status") == "ok":
        for job in changed:
            state["indexed"].append(_index_key(job))

    if not dry_run:
        save_promoted(state, state_path)

    return {
        "open_roles": len(roster),
        "posted": posted,
        "digest": digest_posted,
        "indexnow": indexnow,
        "google": google,
        "messages": messages,
    }
