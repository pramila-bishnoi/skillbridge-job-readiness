"""SkillBridge "Import from Job URL" — route-level tests.

Every test that reaches the fetch step monkeypatches
``app.services.job_url_import.fetch_job_posting_page`` so the suite never
makes a real network request; the SSRF-blocking tests never reach that far
(the block happens before any fetch is attempted), so they run unmocked.
"""

from __future__ import annotations

import pytest

import app.services.job_url_import as job_url_import_module
from app.core.exceptions import JobUrlFetchError
from app.services.job_url_fetch import FetchedPage

JSON_LD_HTML = """
<html><head>
<script type="application/ld+json">
{
  "@type": "JobPosting",
  "title": "Backend Engineer",
  "description": "<p>Join our platform team building services.</p><p>Requirements:</p><ul><li>3-5 years of experience</li><li>Strong Python and FastAPI skills</li><li>Experience with PostgreSQL</li></ul><p>Preferred:</p><ul><li>Familiarity with Docker</li><li>AWS experience</li></ul>",
  "hiringOrganization": {"@type": "Organization", "name": "Acme Corp"},
  "jobLocation": {"@type": "Place", "address": {"@type": "PostalAddress", "addressLocality": "Bengaluru", "addressCountry": "IN"}},
  "employmentType": "FULL_TIME",
  "datePosted": "2026-09-01",
  "baseSalary": {"@type": "MonetaryAmount", "currency": "USD", "value": {"@type": "QuantitativeValue", "minValue": 120000, "maxValue": 150000, "unitText": "YEAR"}}
}
</script>
</head><body></body></html>
"""

HTML_FALLBACK_HTML = """
<html><head><title>Data Analyst Role</title></head>
<body>
  <h1>Data Analyst</h1>
  <p>We need someone comfortable with SQL and Python to join our small analytics team building dashboards.</p>
</body></html>
"""

THIN_PAGE_HTML = "<html><head><title>Careers</title></head><body><nav>Home</nav></body></html>"


def _create_student(client, **overrides):
    payload = {"name": "Jordan Ellis", "email": "jordan.ellis@example.com"}
    payload.update(overrides)
    response = client.post("/api/v1/student/profiles", json=payload)
    assert response.status_code == 201, response.text
    return response.json()["access_token"]


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _mock_fetch(monkeypatch, html: str, url: str = "https://boards.example.com/jobs/42"):
    """Bypasses both the real DNS/SSRF check and the real network fetch, so
    these tests exercise the extraction/preview logic deterministically and
    offline. SSRF *blocking itself* is tested separately below, unmocked,
    against IP-literal URLs that never require DNS."""

    def fake_fetch(target_url: str) -> FetchedPage:
        return FetchedPage(url=url, html=html, content_type="text/html")

    monkeypatch.setattr(job_url_import_module, "fetch_job_posting_page", fake_fetch)
    monkeypatch.setattr(job_url_import_module, "assert_url_is_safe_to_fetch", lambda raw: raw)


def _mock_fetch_raises(monkeypatch, exc: Exception):
    def fake_fetch(target_url: str) -> FetchedPage:
        raise exc

    monkeypatch.setattr(job_url_import_module, "fetch_job_posting_page", fake_fetch)
    monkeypatch.setattr(job_url_import_module, "assert_url_is_safe_to_fetch", lambda raw: raw)


# ------------------------------------------------------------------ success
def test_import_url_json_ld_extracts_full_structured_preview(client, monkeypatch):
    token = _create_student(client)
    _mock_fetch(monkeypatch, JSON_LD_HTML)

    response = client.post(
        "/api/v1/student/jobs/import-url",
        headers=_headers(token),
        json={"url": "https://boards.example.com/jobs/42"},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["extraction_method"] == "JSON_LD"
    assert body["title"] == "Backend Engineer"
    assert body["company"] == "Acme Corp"
    assert body["location"] == "Bengaluru, IN"
    assert body["employment_type"] == "Full-time"
    assert body["compensation"] == "$120,000–$150,000/year"
    assert body["posted_date"] == "2026-09-01"
    assert body["source_url"] == "https://boards.example.com/jobs/42"
    assert body["experience_required"] == "3-5 years"

    required_names = {s["name"] for s in body["required_skills"]}
    preferred_names = {s["name"] for s in body["preferred_skills"]}
    assert required_names == {"Python", "FastAPI", "PostgreSQL"}
    assert preferred_names == {"Docker", "AWS"}
    assert body["warnings"] == []


def test_import_url_preview_is_not_persisted(client, monkeypatch):
    """The preview endpoint must not create a JobProfile row — only the
    existing POST /student/jobs does that, once the student confirms."""
    token = _create_student(client)
    _mock_fetch(monkeypatch, JSON_LD_HTML)

    client.post(
        "/api/v1/student/jobs/import-url",
        headers=_headers(token),
        json={"url": "https://boards.example.com/jobs/42"},
    )

    listed = client.get("/api/v1/student/jobs", headers=_headers(token))
    assert listed.json() == []


def test_confirming_the_preview_saves_through_the_existing_create_endpoint(client, monkeypatch):
    token = _create_student(client)
    _mock_fetch(monkeypatch, JSON_LD_HTML)

    preview = client.post(
        "/api/v1/student/jobs/import-url",
        headers=_headers(token),
        json={"url": "https://boards.example.com/jobs/42"},
    ).json()

    created = client.post(
        "/api/v1/student/jobs",
        headers=_headers(token),
        json={
            "title": preview["title"],
            "company": preview["company"],
            "description": preview["description"],
            "source_url": preview["source_url"],
            "location": preview["location"],
            "employment_type": preview["employment_type"],
            "compensation": preview["compensation"],
            "posted_date": preview["posted_date"],
        },
    )

    assert created.status_code == 201, created.text
    body = created.json()
    assert body["source_url"] == "https://boards.example.com/jobs/42"
    assert body["location"] == "Bengaluru, IN"
    assert body["employment_type"] == "Full-time"
    assert body["compensation"] == "$120,000–$150,000/year"
    assert body["posted_date"] == "2026-09-01"
    required_names = {s["name"] for s in body["required_skills"]}
    assert required_names == {"Python", "FastAPI", "PostgreSQL"}


# --------------------------------------------------------------- fallback
def test_import_url_html_fallback_reports_missing_structured_fields(client, monkeypatch):
    token = _create_student(client)
    _mock_fetch(monkeypatch, HTML_FALLBACK_HTML)

    response = client.post(
        "/api/v1/student/jobs/import-url",
        headers=_headers(token),
        json={"url": "https://careers.example.com/roles/7"},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["extraction_method"] == "HTML_FALLBACK"
    assert body["title"] == "Data Analyst"
    assert body["location"] is None
    assert body["employment_type"] is None
    assert body["compensation"] is None
    assert body["posted_date"] is None
    assert any("JSON-LD" in warning for warning in body["warnings"])
    required_names = {s["name"] for s in body["required_skills"]}
    assert "SQL" in required_names
    assert "Python" in required_names


# ------------------------------------------------------------ invalid URLs
@pytest.mark.parametrize(
    "bad_url",
    ["not a url", "ftp://example.com/job", "javascript:alert(1)", "https://user:pw@x.com/j"],
)
def test_import_url_rejects_invalid_urls(client, bad_url):
    token = _create_student(client)
    response = client.post(
        "/api/v1/student/jobs/import-url", headers=_headers(token), json={"url": bad_url}
    )
    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "INVALID_JOB_URL"


def test_import_url_rejects_an_empty_url_at_the_schema_level(client):
    """Shorter than JobUrlImportRequest.url's min_length — caught by Pydantic
    before the service layer, hence the generic (not job-URL-specific) code."""
    token = _create_student(client)
    response = client.post(
        "/api/v1/student/jobs/import-url", headers=_headers(token), json={"url": ""}
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


# ------------------------------------------------------------------- SSRF
@pytest.mark.parametrize(
    "blocked_url",
    [
        "http://127.0.0.1/job",
        "http://169.254.169.254/latest/meta-data/",
        "http://10.0.0.5/job",
        "http://localhost/job",
        "http://0.0.0.0/job",
    ],
)
def test_import_url_blocks_private_and_internal_addresses(client, blocked_url):
    """No fetch mock here — the SSRF check must reject these before any
    network call is attempted, so this test would fail loudly (via a real,
    slow network attempt) if that guarantee ever broke."""
    token = _create_student(client)
    response = client.post(
        "/api/v1/student/jobs/import-url", headers=_headers(token), json={"url": blocked_url}
    )
    assert response.status_code == 403, response.text
    assert response.json()["error"]["code"] == "JOB_URL_BLOCKED"


# -------------------------------------------------------------- extraction
def test_import_url_reports_extraction_failure_for_a_thin_page(client, monkeypatch):
    token = _create_student(client)
    _mock_fetch(monkeypatch, THIN_PAGE_HTML)

    response = client.post(
        "/api/v1/student/jobs/import-url",
        headers=_headers(token),
        json={"url": "https://example.com/careers"},
    )

    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "JOB_URL_EXTRACTION_FAILED"


def test_import_url_surfaces_a_clean_error_when_the_fetch_fails(client, monkeypatch):
    token = _create_student(client)
    _mock_fetch_raises(monkeypatch, JobUrlFetchError("The page responded with HTTP 404."))

    response = client.post(
        "/api/v1/student/jobs/import-url",
        headers=_headers(token),
        json={"url": "https://example.com/gone"},
    )

    assert response.status_code == 502, response.text
    assert response.json()["error"]["code"] == "JOB_URL_FETCH_FAILED"


# ------------------------------------------------------------------- auth
def test_import_url_requires_authentication(client, monkeypatch):
    _mock_fetch(monkeypatch, JSON_LD_HTML)
    response = client.post(
        "/api/v1/student/jobs/import-url", json={"url": "https://boards.example.com/jobs/42"}
    )
    assert response.status_code == 401
