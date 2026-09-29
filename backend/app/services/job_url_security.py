"""URL validation and SSRF protection for the job-URL-import feature.

A student-supplied URL is the single riskiest input this backend ever makes
an outbound request to, so every check here is deliberately conservative:
only ``http``/``https`` with a resolvable, public hostname is ever allowed
through, and the same check runs again on every redirect hop the fetcher
follows (``services/job_url_fetch.py``) — a public host that later redirects
to ``http://169.254.169.254/`` (a cloud metadata endpoint) must be blocked
just as surely as pasting that address directly.

This does not attempt to defend against DNS-rebinding between this check and
the connection ``httpx`` opens a moment later (that would require pinning
the fetch to the exact resolved IP) — a deliberate, documented scope
decision for a teaching/demo project; see
``docs/SKILLBRIDGE_ARCHITECTURE.md``.
"""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlsplit

from app.core.exceptions import InvalidJobUrlError, JobUrlBlockedError

ALLOWED_SCHEMES = frozenset({"http", "https"})

# Hostnames that are never fetched even if DNS would resolve them somewhere
# (cloud metadata services in particular are reachable at a stable hostname
# on some providers, not only 169.254.169.254).
_BLOCKED_HOSTNAMES = frozenset(
    {"localhost", "metadata.google.internal", "metadata.azure.com"}
)
_BLOCKED_HOSTNAME_SUFFIXES = (".local", ".localhost", ".internal")


def validate_url_syntax(raw_url: str) -> str:
    """Reject anything that is not a well-formed ``http(s)://host/...`` URL.

    Returns the trimmed URL unchanged (no normalization beyond stripping
    surrounding whitespace) so the fetched page's own final URL — not a
    rewritten one — is what gets stored as ``source_url``.
    """
    url = (raw_url or "").strip()
    if not url:
        raise InvalidJobUrlError("Paste a job-posting URL first.")

    parts = urlsplit(url)
    if parts.scheme.lower() not in ALLOWED_SCHEMES:
        raise InvalidJobUrlError("Only http:// and https:// job-posting URLs are supported.")
    if not parts.hostname:
        raise InvalidJobUrlError("That does not look like a valid URL.")
    if parts.username or parts.password:
        raise InvalidJobUrlError("URLs with embedded credentials are not supported.")
    return url


def is_blocked_ip(ip_text: str) -> bool:
    """``True`` when ``ip_text`` must never be fetched by this server."""
    try:
        ip = ipaddress.ip_address(ip_text)
    except ValueError:
        return True  # not even a parseable address => treat as unsafe
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
    )


def assert_host_is_public(hostname: str) -> list[str]:
    """Resolve ``hostname`` and raise if it — or any address it resolves to
    — is not a public, routable address. Returns the resolved IPs.

    Every resolved address is checked, not just the first, because a
    hostname can have multiple A/AAAA records and an attacker only needs one
    of them to be internal.
    """
    lowered = hostname.lower().rstrip(".")
    if lowered in _BLOCKED_HOSTNAMES or lowered.endswith(_BLOCKED_HOSTNAME_SUFFIXES):
        raise JobUrlBlockedError()

    try:
        addr_info = socket.getaddrinfo(hostname, None)
    except socket.gaierror as exc:
        raise InvalidJobUrlError("That URL's host could not be resolved.") from exc

    resolved_ips = sorted({info[4][0] for info in addr_info})
    if not resolved_ips or any(is_blocked_ip(ip) for ip in resolved_ips):
        raise JobUrlBlockedError()
    return resolved_ips


def assert_url_is_safe_to_fetch(url: str) -> str:
    """Combines syntax validation with the SSRF host check. Returns the
    validated URL unchanged; used both for the original URL and for every
    redirect hop."""
    validated = validate_url_syntax(url)
    hostname = urlsplit(validated).hostname
    assert hostname is not None  # guaranteed by validate_url_syntax
    assert_host_is_public(hostname)
    return validated
