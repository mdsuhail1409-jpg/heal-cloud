"""
Automated Tests for Server-Side Request Forgery (SSRF) Protection and Target URL Validation
"""

import pytest
from app.core.ssrf import validate_target_url
from app.core.exceptions import ValidationException


def test_ssrf_block_cloud_metadata_ip():
    """Verify AWS/GCP/Azure link-local metadata IP 169.254.169.254 is strictly blocked."""
    with pytest.raises(ValidationException) as exc:
        validate_target_url("http://169.254.169.254/latest/meta-data/")
    assert "metadata" in str(exc.value).lower()


def test_ssrf_block_cloud_metadata_hostname():
    """Verify cloud metadata hostnames like metadata.google.internal are strictly blocked."""
    with pytest.raises(ValidationException) as exc:
        validate_target_url("http://metadata.google.internal/computeMetadata/v1/")
    assert "metadata" in str(exc.value).lower()


def test_ssrf_block_private_rfc1918_ips():
    """Verify private IPv4 ranges (10.x, 172.16.x, 192.168.x) are blocked."""
    private_urls = [
        "http://10.0.0.1/status",
        "http://172.16.0.50:8080/health",
        "http://192.168.1.100/ping",
    ]
    for url in private_urls:
        with pytest.raises(ValidationException) as exc:
            validate_target_url(url, allow_local_override=False)
        assert "private" in str(exc.value).lower() or "internal" in str(exc.value).lower()


def test_ssrf_block_loopback():
    """Verify loopback addresses (127.0.0.1, localhost) are blocked in standard mode."""
    with pytest.raises(ValidationException) as exc:
        validate_target_url("http://127.0.0.1:8000/health", allow_local_override=False)
    assert "loopback" in str(exc.value).lower() or "localhost" in str(exc.value).lower()


def test_ssrf_block_unsupported_schemes():
    """Verify non-HTTP/HTTPS schemes (ftp, file, gopher) are rejected."""
    unsupported = [
        "ftp://ftp.example.com/health",
        "file:///etc/passwd",
        "gopher://evil.com/7",
    ]
    for url in unsupported:
        with pytest.raises(ValidationException) as exc:
            validate_target_url(url)
        assert "scheme" in str(exc.value).lower()


def test_ssrf_allow_valid_public_targets():
    """Verify valid public targets with standard DNS are accepted."""
    valid_url = "https://api.github.com/zen"
    assert validate_target_url(valid_url) == valid_url

