"""Deterministic HTML/JSON-LD extraction for the job-URL-import feature.

Pure unit tests — no network, no database — against canned HTML strings.
"""

from app.services.job_url_extraction import (
    extract_html_fallback,
    extract_job_posting,
    extract_json_ld,
    strip_html,
)

JSON_LD_JOB_POSTING_HTML = """
<html><head>
<script type="application/ld+json">
{
  "@context": "https://schema.org/",
  "@type": "JobPosting",
  "title": "Backend Engineer",
  "description": "<p>We are looking for a backend engineer to join our platform team.</p><p>Requirements:</p><ul><li>3-5 years of experience</li><li>Strong Python and FastAPI skills</li><li>Experience with PostgreSQL</li></ul><p>Preferred:</p><ul><li>Familiarity with Docker</li><li>AWS experience</li></ul>",
  "hiringOrganization": {"@type": "Organization", "name": "Acme Corp"},
  "jobLocation": {
    "@type": "Place",
    "address": {"@type": "PostalAddress", "addressLocality": "Bengaluru", "addressCountry": "IN"}
  },
  "employmentType": "FULL_TIME",
  "datePosted": "2026-09-01",
  "baseSalary": {
    "@type": "MonetaryAmount",
    "currency": "USD",
    "value": {"@type": "QuantitativeValue", "minValue": 120000, "maxValue": 150000, "unitText": "YEAR"}
  }
}
</script>
</head><body><script>alert('should never run or be parsed as code')</script></body></html>
"""


def test_extract_json_ld_returns_full_structured_posting():
    result = extract_json_ld(JSON_LD_JOB_POSTING_HTML)

    assert result is not None
    assert result.extraction_method == "JSON_LD"
    assert result.title == "Backend Engineer"
    assert result.company == "Acme Corp"
    assert result.location == "Bengaluru, IN"
    assert result.employment_type == "Full-time"
    assert result.compensation == "$120,000–$150,000/year"
    assert result.posted_date == "2026-09-01"
    assert "Requirements:" in result.description
    assert "Preferred:" in result.description
    assert "Strong Python and FastAPI skills" in result.description
    # The <script> tag's text must never appear in the extracted description.
    assert "alert(" not in result.description


def test_extract_json_ld_folds_supplementary_fields_into_description():
    html = """
    <script type="application/ld+json">
    {
      "@type": "JobPosting",
      "title": "Data Analyst",
      "description": "Join our analytics team.",
      "qualifications": "SQL and Python experience required.",
      "skills": "Tableau, Pandas"
    }
    </script>
    """
    result = extract_json_ld(html)

    assert result is not None
    assert result.qualifications == "SQL and Python experience required."
    assert result.technologies == "Tableau, Pandas"
    assert "Qualifications:" in result.description
    assert "Required Skills:" in result.description
    assert "Tableau, Pandas" in result.description


def test_extract_json_ld_handles_graph_wrapper_and_array_employment_type():
    html = """
    <script type="application/ld+json">
    {
      "@context": "https://schema.org",
      "@graph": [
        {"@type": "WebPage", "name": "irrelevant"},
        {
          "@type": "JobPosting",
          "title": "Contract Designer",
          "description": "Design work for a 6 month engagement.",
          "employmentType": ["CONTRACTOR", "PART_TIME"]
        }
      ]
    }
    </script>
    """
    result = extract_json_ld(html)

    assert result is not None
    assert result.title == "Contract Designer"
    assert result.employment_type == "Contract, Part-time"


def test_extract_json_ld_returns_none_when_no_job_posting_present():
    html = """
    <script type="application/ld+json">
    {"@type": "Organization", "name": "Acme Corp"}
    </script>
    """
    assert extract_json_ld(html) is None


def test_extract_json_ld_ignores_malformed_json():
    html = '<script type="application/ld+json">{not valid json,,,</script>'
    assert extract_json_ld(html) is None


def test_extract_html_fallback_reads_title_and_strips_boilerplate():
    html = """
    <html><head><title>Frontend Engineer - Careers</title></head>
    <body>
      <nav>Home | Careers | About</nav>
      <script>console.log('never executed or read as code')</script>
      <style>.job { color: red; }</style>
      <h1>Frontend Engineer</h1>
      <p>We build delightful React interfaces.</p>
      <p>Requirements:</p>
      <ul><li>React experience</li><li>TypeScript</li></ul>
    </body></html>
    """
    result = extract_html_fallback(html)

    assert result.extraction_method == "HTML_FALLBACK"
    assert result.title == "Frontend Engineer"  # h1 preferred over <title>
    # Fields that unstructured HTML cannot reliably provide are left null,
    # never guessed.
    assert result.location is None
    assert result.employment_type is None
    assert result.compensation is None
    assert result.posted_date is None
    assert "React experience" in result.description
    assert "console.log" not in result.description
    assert "color: red" not in result.description


def test_extract_html_fallback_falls_back_to_title_tag_when_no_h1():
    html = "<html><head><title>Backend Role</title></head><body><p>Some description text here.</p></body></html>"
    result = extract_html_fallback(html)
    assert result.title == "Backend Role"


def test_extract_job_posting_prefers_json_ld_over_fallback():
    result = extract_job_posting(JSON_LD_JOB_POSTING_HTML)
    assert result.extraction_method == "JSON_LD"


def test_extract_job_posting_uses_fallback_when_no_json_ld():
    html = "<html><body><h1>Some Role</h1><p>A description of the role goes here.</p></body></html>"
    result = extract_job_posting(html)
    assert result.extraction_method == "HTML_FALLBACK"


def test_strip_html_discards_script_and_style_content():
    html = "<div>Visible<script>evil()</script><style>.a{}</style> text</div>"
    assert strip_html(html) == "Visible text"
