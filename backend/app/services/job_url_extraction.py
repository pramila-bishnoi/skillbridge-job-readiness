"""Deterministic extraction of structured job-posting fields from HTML.

No external LLM/NLP — the same posture as every other matching module in
this codebase (``services/job_analysis.py``, ``services/skill_normalization.py``).
Two strategies, tried in order:

1. ``extract_json_ld`` — schema.org ``JobPosting`` structured data, embedded
   as ``<script type="application/ld+json">``. Most job boards and ATSs
   (LinkedIn, Indeed, Greenhouse, Lever, Workday, and most company career
   pages) already publish this for search-engine indexing, so it is the
   richest and most reliable source when present.
2. ``extract_html_fallback`` — when no ``JobPosting`` JSON-LD is found,
   deterministic tag-stripping recovers a plain-text description plus a
   best-effort title. It never guesses location, employment type,
   compensation, or a posted date from free text — those fields stay
   ``None`` rather than being invented (the same "never invents facts" rule
   ``services/job_analysis.py`` follows for experience requirements).

``<script>``/``<style>``/``<noscript>`` content is always discarded before
any text is read out of the page — the fetched page's JavaScript is never
parsed as code, only ever thrown away as inert markup.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from html import unescape
from html.parser import HTMLParser
from typing import Any

# --------------------------------------------------------------- HTML -> text
_BLOCK_TAGS = frozenset(
    {
        "p", "div", "li", "br", "h1", "h2", "h3", "h4", "h5", "h6",
        "tr", "section", "article", "ul", "ol", "header", "footer", "table",
    }
)
_SKIP_TAGS = frozenset({"script", "style", "noscript", "svg", "head"})


class _TextExtractor(HTMLParser):
    """Strips tags, turns block-element boundaries into newlines, and
    entirely discards ``<script>``/``<style>``/``<noscript>`` content."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._chunks: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in _SKIP_TAGS:
            self._skip_depth += 1
        elif tag in _BLOCK_TAGS:
            self._chunks.append("\n")

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in _BLOCK_TAGS:
            self._chunks.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in _SKIP_TAGS:
            self._skip_depth = max(0, self._skip_depth - 1)
        elif tag in _BLOCK_TAGS:
            self._chunks.append("\n")

    def handle_data(self, data: str) -> None:
        if self._skip_depth == 0:
            self._chunks.append(data)

    def text(self) -> str:
        raw = "".join(self._chunks)
        lines = [re.sub(r"[ \t]+", " ", line).strip() for line in raw.splitlines()]
        collapsed: list[str] = []
        blank_run = 0
        for line in lines:
            if line:
                collapsed.append(line)
                blank_run = 0
            else:
                blank_run += 1
                if blank_run <= 1:
                    collapsed.append("")
        return "\n".join(collapsed).strip()


def strip_html(html: str) -> str:
    """Plain text with block-level boundaries preserved as newlines, so the
    existing header-based segmentation in ``services/job_analysis.py`` (which
    looks for a heading like "Requirements:" on its own line) still works on
    the result."""
    parser = _TextExtractor()
    parser.feed(html)
    parser.close()
    return parser.text()


# ----------------------------------------------------------------- schema.org
@dataclass(frozen=True)
class ExtractedJobPosting:
    title: str | None
    company: str | None
    location: str | None
    employment_type: str | None
    compensation: str | None
    posted_date: str | None
    responsibilities: str | None
    qualifications: str | None
    technologies: str | None
    description: str
    extraction_method: str  # "JSON_LD" | "HTML_FALLBACK"


_JSON_LD_RE = re.compile(
    r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
    re.IGNORECASE | re.DOTALL,
)


def _iter_json_ld_blocks(html: str) -> list[Any]:
    items: list[Any] = []
    for match in _JSON_LD_RE.finditer(html):
        raw = match.group(1).strip()
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            continue
        if isinstance(data, list):
            items.extend(data)
        elif isinstance(data, dict) and isinstance(data.get("@graph"), list):
            items.extend(data["@graph"])
        else:
            items.append(data)
    return items


def _find_job_posting(html: str) -> dict[str, Any] | None:
    for item in _iter_json_ld_blocks(html):
        if not isinstance(item, dict):
            continue
        type_field = item.get("@type")
        types = type_field if isinstance(type_field, list) else [type_field]
        if any(isinstance(t, str) and t.casefold() == "jobposting" for t in types):
            return item
    return None


def _text_or_none(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        text = strip_html(value) if "<" in value else unescape(value)
        text = text.strip()
        return text or None
    if isinstance(value, list):
        parts = [p for p in (_text_or_none(v) for v in value) if p]
        return "\n".join(parts) if parts else None
    if isinstance(value, dict):
        return _text_or_none(value.get("value") or value.get("name"))
    return _text_or_none(str(value))


def _company_name(hiring_org: Any) -> str | None:
    if isinstance(hiring_org, dict):
        return _text_or_none(hiring_org.get("name"))
    return _text_or_none(hiring_org)


def _location_text(job_location: Any, job_location_type: Any) -> str | None:
    candidates = job_location if isinstance(job_location, list) else [job_location]
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        address = candidate.get("address")
        if isinstance(address, str) and address.strip():
            return address.strip()
        if isinstance(address, dict):
            parts = [
                address.get("addressLocality"),
                address.get("addressRegion"),
                address.get("addressCountry"),
            ]
            joined = ", ".join(p.strip() for p in parts if isinstance(p, str) and p.strip())
            if joined:
                return joined
    if isinstance(job_location_type, str) and job_location_type.strip().upper() == "TELECOMMUTE":
        return "Remote"
    return None


_EMPLOYMENT_TYPE_LABELS = {
    "FULL_TIME": "Full-time",
    "PART_TIME": "Part-time",
    "CONTRACTOR": "Contract",
    "TEMPORARY": "Temporary",
    "INTERN": "Internship",
    "VOLUNTEER": "Volunteer",
    "PER_DIEM": "Per diem",
    "OTHER": "Other",
}


def _employment_type_text(value: Any) -> str | None:
    values = value if isinstance(value, list) else [value]
    labels: list[str] = []
    for item in values:
        if not isinstance(item, str) or not item.strip():
            continue
        key = item.strip().upper().replace("-", "_").replace(" ", "_")
        label = _EMPLOYMENT_TYPE_LABELS.get(key, item.strip().title())
        if label not in labels:
            labels.append(label)
    return ", ".join(labels) or None


_CURRENCY_SYMBOLS = {"USD": "$", "EUR": "€", "GBP": "£", "INR": "₹", "JPY": "¥"}
_UNIT_LABELS = {"YEAR": "year", "HOUR": "hour", "MONTH": "month", "WEEK": "week", "DAY": "day"}


def _fmt_amount(value: Any) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if number == int(number):
        return f"{int(number):,}"
    return f"{number:,.2f}"


def _compensation_text(base_salary: Any) -> str | None:
    if not isinstance(base_salary, dict):
        return None
    currency = base_salary.get("currency")
    symbol = _CURRENCY_SYMBOLS.get(str(currency).upper(), f"{currency} " if currency else "")
    value = base_salary.get("value")

    amount_text: str | None = None
    unit: Any = None
    if isinstance(value, dict):
        unit = value.get("unitText")
        min_v, max_v, single = value.get("minValue"), value.get("maxValue"), value.get("value")
        if min_v is not None and max_v is not None:
            amount_text = f"{symbol}{_fmt_amount(min_v)}–{symbol}{_fmt_amount(max_v)}"
        elif single is not None:
            amount_text = f"{symbol}{_fmt_amount(single)}"
    elif isinstance(value, (int, float, str)):
        amount_text = f"{symbol}{_fmt_amount(value)}"

    if amount_text is None:
        return None
    if unit:
        amount_text += f"/{_UNIT_LABELS.get(str(unit).upper(), str(unit).lower())}"
    return amount_text


def _combine_description(
    base: str, responsibilities: str | None, qualifications: str | None, technologies: str | None
) -> str:
    """Folds the supplementary JSON-LD fields into the description using
    the *exact* section headings ``services/job_analysis.segment_description``
    already recognizes ("Qualifications", "Required Skills"), so the
    existing, unmodified Phase 3 pipeline classifies them correctly without
    this module needing any knowledge of that header list itself."""
    parts = [base.strip()] if base.strip() else []
    if responsibilities and responsibilities.strip() not in base:
        parts.append(f"Responsibilities:\n{responsibilities.strip()}")
    if qualifications and qualifications.strip() not in base:
        parts.append(f"Qualifications:\n{qualifications.strip()}")
    if technologies and technologies.strip() not in base:
        parts.append(f"Required Skills:\n{technologies.strip()}")
    return "\n\n".join(parts).strip()


def extract_json_ld(html: str) -> ExtractedJobPosting | None:
    posting = _find_job_posting(html)
    if posting is None:
        return None

    title = _text_or_none(posting.get("title"))
    company = _company_name(posting.get("hiringOrganization"))
    location = _location_text(posting.get("jobLocation"), posting.get("jobLocationType"))
    employment_type = _employment_type_text(posting.get("employmentType"))
    compensation = _compensation_text(posting.get("baseSalary"))
    posted_date = _text_or_none(posting.get("datePosted"))
    responsibilities = _text_or_none(posting.get("responsibilities"))
    qualifications = _text_or_none(posting.get("qualifications"))
    technologies = _text_or_none(posting.get("skills"))
    base_description = _text_or_none(posting.get("description")) or ""

    description = _combine_description(base_description, responsibilities, qualifications, technologies)

    return ExtractedJobPosting(
        title=title,
        company=company,
        location=location,
        employment_type=employment_type,
        compensation=compensation,
        posted_date=posted_date,
        responsibilities=responsibilities,
        qualifications=qualifications,
        technologies=technologies,
        description=description,
        extraction_method="JSON_LD",
    )


# ------------------------------------------------------------------ fallback
_TITLE_TAG_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
_H1_RE = re.compile(r"<h1[^>]*>(.*?)</h1>", re.IGNORECASE | re.DOTALL)
_OG_SITE_NAME_RE = re.compile(
    r'<meta[^>]+property=["\']og:site_name["\'][^>]+content=["\']([^"\']*)["\']', re.IGNORECASE
)


def extract_html_fallback(html: str) -> ExtractedJobPosting:
    """No JSON-LD ``JobPosting`` was found. Recovers only what can be read
    directly off the page without guessing: a title, an ``og:site_name``
    company if present, and the page's full visible text as the
    description. Location, employment type, compensation, and posted date
    are left ``None`` — unstructured HTML does not reliably distinguish
    those from surrounding boilerplate, and this codebase never invents a
    value it cannot point to (the same rule ``extract_experience`` follows)."""
    title = None
    if match := _H1_RE.search(html):
        title = strip_html(match.group(1)).strip() or None
    if not title and (match := _TITLE_TAG_RE.search(html)):
        title = unescape(re.sub(r"<[^>]+>", "", match.group(1))).strip() or None

    company = None
    if match := _OG_SITE_NAME_RE.search(html):
        company = unescape(match.group(1)).strip() or None

    description = strip_html(html)

    return ExtractedJobPosting(
        title=title,
        company=company,
        location=None,
        employment_type=None,
        compensation=None,
        posted_date=None,
        responsibilities=None,
        qualifications=None,
        technologies=None,
        description=description,
        extraction_method="HTML_FALLBACK",
    )


def extract_job_posting(html: str) -> ExtractedJobPosting:
    return extract_json_ld(html) or extract_html_fallback(html)
