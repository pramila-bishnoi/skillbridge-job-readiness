"""Safe, bounded fetch of a single public job-posting page.

This module makes the *only* outbound HTTP request in the job-URL-import
feature. It deliberately:

- never executes any fetched JavaScript — the response body is only ever
  read as text and handed to ``services/job_url_extraction.py`` for regex/
  stdlib-HTML-parser extraction, never to a browser or a JS runtime;
- never attempts to log in, solve a CAPTCHA, or work around a paywall — a
  single anonymous GET, and a failure (401/403/429, a CAPTCHA page) is
  surfaced to the student as a clean "could not fetch" error, not retried
  with different credentials or headers;
- respects ``robots.txt`` for the target host, the same as any well-behaved
  crawler, rather than bypassing it;
- re-validates every redirect hop through ``job_url_security`` before
  following it, so a URL that is safe at the start cannot redirect its way
  to an internal address;
- bounds the response size (streamed, aborted once the cap is hit) so a
  malicious or misbehaving server cannot exhaust memory.
"""

from __future__ import annotations

from dataclasses import dataclass
from urllib import robotparser
from urllib.parse import urljoin, urlsplit

import httpx

from app.core.config import settings
from app.core.exceptions import JobUrlFetchError, JobUrlRobotsDisallowedError
from app.services.job_url_security import assert_url_is_safe_to_fetch

USER_AGENT = "SkillBridgeJobImportBot/1.0 (+student job-readiness coach; single-page fetch, no JS)"

_NON_HTML_CONTENT_PREFIXES = (
    "image/",
    "video/",
    "audio/",
    "application/pdf",
    "application/octet-stream",
    "application/zip",
    "font/",
)


@dataclass(frozen=True)
class FetchedPage:
    url: str  # the final URL, after any redirects actually followed
    html: str
    content_type: str


def _robots_allow(url: str) -> bool:
    """Best-effort ``robots.txt`` check. A missing or unreachable robots.txt
    means "no restrictions published" (the standard crawler convention) —
    only an explicit ``Disallow`` blocks the fetch."""
    parts = urlsplit(url)
    robots_url = f"{parts.scheme}://{parts.netloc}/robots.txt"
    try:
        assert_url_is_safe_to_fetch(robots_url)
        response = httpx.get(
            robots_url,
            timeout=settings.job_url_fetch_timeout_seconds,
            headers={"User-Agent": USER_AGENT},
            follow_redirects=False,
        )
    except httpx.HTTPError:
        return True
    if response.status_code >= 400:
        return True

    parser = robotparser.RobotFileParser()
    parser.parse(response.text.splitlines())
    return parser.can_fetch(USER_AGENT, url)


def fetch_job_posting_page(url: str) -> FetchedPage:
    """Fetch ``url`` (already validated by the caller) and return its HTML.

    Raises ``JobUrlRobotsDisallowedError`` or ``JobUrlFetchError`` — never
    lets an ``httpx`` exception escape this module.
    """
    if not _robots_allow(url):
        raise JobUrlRobotsDisallowedError()

    current_url = url
    for _hop in range(settings.job_url_max_redirects + 1):
        try:
            with httpx.stream(
                "GET",
                current_url,
                timeout=settings.job_url_fetch_timeout_seconds,
                headers={"User-Agent": USER_AGENT, "Accept": "text/html,*/*;q=0.5"},
                follow_redirects=False,
            ) as response:
                if response.is_redirect:
                    location = response.headers.get("location")
                    if not location:
                        raise JobUrlFetchError("The server redirected without a destination.")
                    current_url = assert_url_is_safe_to_fetch(urljoin(current_url, location))
                    continue

                if response.status_code >= 400:
                    raise JobUrlFetchError(f"The page responded with HTTP {response.status_code}.")

                content_type = response.headers.get("content-type", "").split(";")[0].strip().lower()
                if content_type.startswith(_NON_HTML_CONTENT_PREFIXES):
                    raise JobUrlFetchError("That URL does not point to an HTML page.")

                body = bytearray()
                for chunk in response.iter_bytes():
                    body.extend(chunk)
                    if len(body) > settings.job_url_max_response_bytes:
                        raise JobUrlFetchError("The page was too large to fetch.")

                html = body.decode(response.encoding or "utf-8", errors="replace")
                return FetchedPage(
                    url=str(response.url), html=html, content_type=content_type
                )
        except httpx.TimeoutException as exc:
            raise JobUrlFetchError("The request to that URL timed out.") from exc
        except httpx.HTTPError as exc:
            raise JobUrlFetchError("Could not reach that URL.") from exc

    raise JobUrlFetchError("Too many redirects.")
