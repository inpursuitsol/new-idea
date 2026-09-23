"""Fetch and describe live jobs on inpursuit.co.in."""

from __future__ import annotations

import html
import json
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from urllib.request import Request

import yaml

from pehli_salary.config import JOBS_GROWTH_PATH

USER_AGENT = "InPursuitJobsGrowth/1.0"


@dataclass(frozen=True)
class GrowthConfig:
    site: str
    jobs_api: str
    hub_url: str
    indexnow_key: str
    utm_source: str
    utm_medium: str
    utm_campaign: str
    promote_limit: int = 2

    @property
    def host(self) -> str:
        return urlsplit(self.site).netloc

    @property
    def indexnow_key_location(self) -> str:
        return f"https://{self.host}/{self.indexnow_key}.txt"


@dataclass(frozen=True)
class SiteJob:
    job_id: str
    slug: str
    title: str
    link: str
    modified: str
    summary: str
    city: str


@dataclass(frozen=True)
class AuditIssue:
    code: str
    url: str
    detail: str


def load_growth_config(path: Path | None = None) -> GrowthConfig:
    config_path = path or JOBS_GROWTH_PATH
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    return GrowthConfig(
        site=str(raw["site"]).rstrip("/"),
        jobs_api=str(raw["jobs_api"]),
        hub_url=str(raw["hub_url"]),
        indexnow_key=str(raw["indexnow_key"]).strip(),
        utm_source=str(raw.get("utm_source") or "telegram"),
        utm_medium=str(raw.get("utm_medium") or "social"),
        utm_campaign=str(raw.get("utm_campaign") or "inpursuit-jobs"),
        promote_limit=int(raw.get("promote_limit") or 2),
    )


def decode_text(value: str) -> str:
    return html.unescape(value or "").replace("\xa0", " ").strip()


def html_to_text(value: str) -> str:
    text = re.sub(r"<[^>]+>", " ", value or "")
    text = decode_text(text)
    return re.sub(r"\s+", " ", text).strip()


def summarize(value: str, limit: int = 180) -> str:
    text = html_to_text(value)
    if len(text) <= limit:
        return text
    cut = text[: limit - 1].rsplit(" ", 1)[0].rstrip(".,;:")
    return cut + "…"


def guess_city(title: str) -> str:
    parts = [part.strip() for part in re.split(r"\s+[–—-]\s+", title) if part.strip()]
    if len(parts) < 2:
        return ""

    def looks_like_place(part: str) -> bool:
        if re.search(r"\d|lpa|year", part, re.I):
            return False
        return 2 <= len(part) <= 32

    if looks_like_place(parts[-1]):
        return parts[-1]
    if len(parts) >= 3 and looks_like_place(parts[-2]):
        return parts[-2]
    return ""


def tracked_url(url: str, config: GrowthConfig, *, campaign: str | None = None) -> str:
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query["utm_source"] = config.utm_source
    query["utm_medium"] = config.utm_medium
    query["utm_campaign"] = campaign or config.utm_campaign
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), ""))


def job_from_api(raw: dict) -> SiteJob:
    title = decode_text((raw.get("title") or {}).get("rendered") or "")
    content = (raw.get("content") or {}).get("rendered") or ""
    link = str(raw.get("link") or "").strip()
    return SiteJob(
        job_id=str(raw.get("id") or ""),
        slug=str(raw.get("slug") or ""),
        title=title,
        link=link,
        modified=str(raw.get("modified") or raw.get("date") or ""),
        summary=summarize(content),
        city=guess_city(title),
    )


def fetch_text(url: str, *, timeout: int = 30) -> tuple[str, dict[str, str]]:
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json, text/html"})
    with _urlopen(request, timeout=timeout) as response:
        body = response.read().decode("utf-8", errors="replace")
        headers = {key.lower(): value for key, value in response.headers.items()}
        return body, headers


def _urlopen(request: Request, timeout: int = 30):
    import urllib.request

    return urllib.request.urlopen(request, timeout=timeout)


def fetch_jobs(config: GrowthConfig, *, per_page: int = 50) -> list[SiteJob]:
    jobs: list[SiteJob] = []
    page = 1
    total_pages = 1
    while page <= total_pages:
        url = f"{config.jobs_api}?per_page={per_page}&page={page}&status=publish"
        body, headers = fetch_text(url)
        payload = json.loads(body)
        if isinstance(payload, dict):
            raise RuntimeError(f"Jobs API error: {payload.get('message') or payload}")
        jobs.extend(job_from_api(item) for item in payload if item.get("status", "publish") == "publish")
        total_pages = int(headers.get("x-wp-totalpages") or 1)
        page += 1
    jobs.sort(key=lambda job: job.modified, reverse=True)
    return jobs


def format_job_post(job: SiteJob, config: GrowthConfig) -> str:
    place = job.city or "India"
    lines = [
        "📢 OPEN ROLE — InPursuit",
        "",
        job.title,
        place,
        "",
    ]
    if job.summary:
        lines.extend([job.summary, ""])
    lines.extend(
        [
            "CV yahin bhejo. Apply is free and goes straight to InPursuit:",
            tracked_url(job.link, config),
            "",
            "Saari open roles:",
            tracked_url(config.hub_url, config, campaign=f"{config.utm_campaign}-hub"),
        ]
    )
    return "\n".join(lines)


def format_digest(jobs: list[SiteJob], config: GrowthConfig) -> str:
    shown = jobs[:8]
    noun = "role" if len(jobs) == 1 else "roles"
    lines = [
        "📋 JOBS — inpursuit.co.in/jobs",
        "",
        f"{len(jobs)} open {noun}. CV directly on the site.",
        "",
    ]
    for job in shown:
        place = f" · {job.city}" if job.city else ""
        lines.append(f"• {job.title}{place}")
        lines.append(tracked_url(job.link, config))
    extra = len(jobs) - len(shown)
    if extra:
        lines.append(f"…and {extra} more")
    lines.extend(
        [
            "",
            "Full list:",
            tracked_url(config.hub_url, config, campaign=f"{config.utm_campaign}-hub"),
        ]
    )
    return "\n".join(lines)


def extract_jsonld(html_text: str) -> list[dict]:
    blocks = re.findall(
        r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        html_text,
        flags=re.I | re.S,
    )
    found: list[dict] = []
    for block in blocks:
        try:
            data = json.loads(block)
        except json.JSONDecodeError:
            continue
        found.extend(_flatten_jsonld(data))
    return found


def _flatten_jsonld(data: object) -> list[dict]:
    if isinstance(data, list):
        out: list[dict] = []
        for item in data:
            out.extend(_flatten_jsonld(item))
        return out
    if not isinstance(data, dict):
        return []
    graph = data.get("@graph")
    if isinstance(graph, list):
        return _flatten_jsonld(graph)
    return [data]


def _parse_day(value: str) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def audit_hub(html_text: str, hub_url: str) -> list[AuditIssue]:
    issues: list[AuditIssue] = []
    if not re.search(r'<link[^>]+rel=["\']canonical["\']', html_text, re.I):
        issues.append(AuditIssue("hub_missing_canonical", hub_url, "Jobs hub has no canonical URL."))
    types = {str(block.get("@type") or "") for block in extract_jsonld(html_text)}
    if "ItemList" not in types and "CollectionPage" not in types:
        issues.append(
            AuditIssue(
                "hub_missing_itemlist",
                hub_url,
                "Jobs hub has no ItemList or CollectionPage structured data.",
            )
        )
    return issues


def audit_job_page(html_text: str, url: str, *, today: date) -> list[AuditIssue]:
    issues: list[AuditIssue] = []
    posting = next((block for block in extract_jsonld(html_text) if block.get("@type") == "JobPosting"), None)
    if posting is None:
        return [AuditIssue("jobposting_missing", url, "Role page has no JobPosting structured data.")]

    title = str(posting.get("title") or "")
    if re.search(r"&#\d+;|&[a-z]+;", title, re.I):
        issues.append(AuditIssue("title_html_entity", url, "JobPosting title still contains HTML entities."))

    description = html_to_text(str(posting.get("description") or ""))
    if len(description) < 150:
        issues.append(AuditIssue("description_short", url, "JobPosting description is under 150 characters."))

    required = {
        "datePosted": posting.get("datePosted"),
        "hiringOrganization": (posting.get("hiringOrganization") or {}).get("name")
        if isinstance(posting.get("hiringOrganization"), dict)
        else posting.get("hiringOrganization"),
        "jobLocation": posting.get("jobLocation"),
    }
    for field, value in required.items():
        if not value:
            issues.append(AuditIssue("missing_field", url, f"JobPosting is missing {field}."))

    valid = _parse_day(str(posting.get("validThrough") or ""))
    if valid is not None and valid < today:
        issues.append(AuditIssue("valid_through_past", url, f"validThrough {valid.isoformat()} is in the past."))

    if re.search(r"\d+\s*lpa", title, re.I) and not posting.get("baseSalary"):
        issues.append(
            AuditIssue(
                "salary_claim_without_base_salary",
                url,
                "Title states a salary but JobPosting has no baseSalary.",
            )
        )
    return issues


def run_audit(config: GrowthConfig | None = None, *, today: date | None = None) -> dict:
    from pehli_salary.queue import today_ist

    growth = config or load_growth_config()
    day = today or today_ist()
    hub_html, _headers = fetch_text(growth.hub_url)
    issues = audit_hub(hub_html, growth.hub_url)
    jobs = fetch_jobs(growth)
    for job in jobs:
        page, _headers = fetch_text(job.link)
        issues.extend(audit_job_page(page, job.link, today=day))
    return {
        "hub": growth.hub_url,
        "open_roles": len(jobs),
        "issues": [{"code": issue.code, "url": issue.url, "detail": issue.detail} for issue in issues],
    }


def indexnow_payload(urls: list[str], config: GrowthConfig) -> dict:
    unique: list[str] = []
    for url in urls:
        if url and url not in unique:
            unique.append(url)
    return {
        "host": config.host,
        "key": config.indexnow_key,
        "keyLocation": config.indexnow_key_location,
        "urlList": unique[:10000],
    }
