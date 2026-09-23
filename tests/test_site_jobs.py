from __future__ import annotations

from datetime import date

from pehli_salary.site_jobs import (
    GrowthConfig,
    audit_hub,
    audit_job_page,
    format_digest,
    format_job_post,
    guess_city,
    indexnow_payload,
    job_from_api,
    tracked_url,
)


def _config() -> GrowthConfig:
    return GrowthConfig(
        site="https://inpursuit.co.in",
        jobs_api="https://inpursuit.co.in/wp-json/wp/v2/job",
        hub_url="https://inpursuit.co.in/jobs/",
        indexnow_key="abc123key",
        utm_source="telegram",
        utm_medium="social",
        utm_campaign="inpursuit-jobs",
    )


def _job():
    return job_from_api(
        {
            "id": 73,
            "slug": "python-full-stack-developer-hyderabad-50-lpa",
            "link": "https://inpursuit.co.in/jobs/python-full-stack-developer-hyderabad-50-lpa/",
            "modified": "2026-09-15T17:45:33",
            "status": "publish",
            "title": {"rendered": "Python Full Stack Developer &#8211; Hyderabad &#8211; 50 LPA"},
            "content": {
                "rendered": "<p>Build APIs and ship features for a product team in Hyderabad. "
                "Apply with your resume on this page. Experience with Django and React is useful.</p>"
            },
        }
    )


def test_job_from_api_decodes_title_and_city():
    job = _job()
    assert "–" in job.title
    assert "&#" not in job.title
    assert job.city == "Hyderabad"
    assert job.job_id == "73"
    assert job.summary.startswith("Build APIs")


def test_guess_city_without_salary_suffix():
    assert guess_city("Production Control Engineer – Bangalore") == "Bangalore"
    assert guess_city("Accountant") == ""


def test_tracked_url_points_at_jobs_hub():
    url = tracked_url("https://inpursuit.co.in/jobs/", _config(), campaign="inpursuit-jobs-hub")
    assert url.startswith("https://inpursuit.co.in/jobs/?")
    assert "utm_source=telegram" in url
    assert "utm_campaign=inpursuit-jobs-hub" in url


def test_format_job_post_links_role_and_hub():
    text = format_job_post(_job(), _config())
    assert "Python Full Stack Developer" in text
    assert "https://inpursuit.co.in/jobs/python-full-stack-developer-hyderabad-50-lpa/" in text
    assert "https://inpursuit.co.in/jobs/" in text
    assert "utm_campaign=inpursuit-jobs-hub" in text


def test_format_digest_lists_hub():
    text = format_digest([_job()], _config())
    assert "inpursuit.co.in/jobs" in text
    assert "1 open role" in text
    assert "Hyderabad" in text


def test_audit_hub_flags_missing_discovery_tags():
    issues = audit_hub("<html><title>Jobs</title></html>", "https://inpursuit.co.in/jobs/")
    codes = {issue.code for issue in issues}
    assert codes == {"hub_missing_canonical", "hub_missing_itemlist"}


def test_audit_job_page_flags_entities_and_salary_claim():
    html = """
    <html><head>
    <script type="application/ld+json">
    {"@context":"https://schema.org/","@type":"JobPosting","title":"Developer &#8211; 50 LPA",
     "description":"Short","datePosted":"2026-09-15",
     "hiringOrganization":{"@type":"Organization","name":"InPursuit"},
     "jobLocation":{"@type":"Place","address":{"addressLocality":"Hyderabad"}}}
    </script>
    </head></html>
    """
    issues = audit_job_page(html, "https://inpursuit.co.in/jobs/example/", today=date(2026, 9, 23))
    codes = {issue.code for issue in issues}
    assert "title_html_entity" in codes
    assert "description_short" in codes
    assert "salary_claim_without_base_salary" in codes


def test_audit_job_page_flags_expired_posting():
    html = """
    <script type="application/ld+json">
    {"@type":"JobPosting","title":"Accountant","description":"%s",
     "datePosted":"2026-01-01","validThrough":"2026-02-01",
     "hiringOrganization":{"name":"InPursuit"},"jobLocation":{"address":{"addressLocality":"Pune"}}}
    </script>
    """ % ("word " * 40)
    issues = audit_job_page(html, "https://inpursuit.co.in/jobs/accountant/", today=date(2026, 9, 23))
    assert any(issue.code == "valid_through_past" for issue in issues)


def test_indexnow_payload_uses_site_host():
    payload = indexnow_payload(
        [
            "https://inpursuit.co.in/jobs/",
            "https://inpursuit.co.in/jobs/",
            "https://inpursuit.co.in/jobs/accountant/",
        ],
        _config(),
    )
    assert payload["host"] == "inpursuit.co.in"
    assert payload["keyLocation"] == "https://inpursuit.co.in/abc123key.txt"
    assert payload["urlList"] == [
        "https://inpursuit.co.in/jobs/",
        "https://inpursuit.co.in/jobs/accountant/",
    ]
