"""URL validation and SSRF protection for the job-URL-import feature.

Pure unit tests against IP literals only (never a real hostname) so this
suite never depends on DNS or network access being available in CI.
"""

import pytest

from app.core.exceptions import InvalidJobUrlError, JobUrlBlockedError
from app.services.job_url_security import (
    assert_host_is_public,
    assert_url_is_safe_to_fetch,
    is_blocked_ip,
    validate_url_syntax,
)


@pytest.mark.parametrize(
    "url",
    [
        "not a url",
        "ftp://example.com/job",
        "javascript:alert(1)",
        "file:///etc/passwd",
        "",
        "   ",
        "https://",
        "https://user:pass@example.com/job",
    ],
)
def test_validate_url_syntax_rejects_bad_input(url):
    with pytest.raises(InvalidJobUrlError):
        validate_url_syntax(url)


@pytest.mark.parametrize("url", ["http://example.com/job", "https://boards.example.com/jobs/1"])
def test_validate_url_syntax_accepts_well_formed_http_urls(url):
    assert validate_url_syntax(url) == url


@pytest.mark.parametrize(
    "ip",
    [
        "127.0.0.1",       # loopback
        "10.0.0.5",        # private
        "172.16.4.4",      # private
        "192.168.1.1",     # private
        "169.254.169.254",  # link-local / cloud metadata
        "0.0.0.0",         # unspecified
        "::1",             # IPv6 loopback
        "fc00::1",         # IPv6 unique local (private)
        "not-an-ip",
    ],
)
def test_is_blocked_ip_flags_private_and_reserved_addresses(ip):
    assert is_blocked_ip(ip) is True


@pytest.mark.parametrize("ip", ["93.184.216.34", "8.8.8.8", "1.1.1.1"])
def test_is_blocked_ip_allows_public_addresses(ip):
    assert is_blocked_ip(ip) is False


@pytest.mark.parametrize(
    "hostname",
    ["127.0.0.1", "169.254.169.254", "10.1.2.3", "0.0.0.0", "localhost"],
)
def test_assert_host_is_public_blocks_internal_hosts(hostname):
    with pytest.raises(JobUrlBlockedError):
        assert_host_is_public(hostname)


def test_assert_host_is_public_allows_a_public_ip_literal():
    resolved = assert_host_is_public("93.184.216.34")
    assert resolved == ["93.184.216.34"]


def test_assert_url_is_safe_to_fetch_blocks_private_ip_url():
    with pytest.raises(JobUrlBlockedError):
        assert_url_is_safe_to_fetch("http://127.0.0.1:8000/job")


def test_assert_url_is_safe_to_fetch_blocks_cloud_metadata_endpoint():
    with pytest.raises(JobUrlBlockedError):
        assert_url_is_safe_to_fetch("http://169.254.169.254/latest/meta-data/")


def test_assert_url_is_safe_to_fetch_allows_public_ip_literal_url():
    assert assert_url_is_safe_to_fetch("http://93.184.216.34/job") == "http://93.184.216.34/job"
