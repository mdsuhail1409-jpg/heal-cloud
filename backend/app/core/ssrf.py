"""
Server-Side Request Forgery (SSRF) Protection and Target URL Validation
"""

import ipaddress
import socket
from urllib.parse import urlparse
from app.core.config import settings
from app.core.exceptions import ValidationException

# Known cloud metadata IP addresses and hostnames that are strictly prohibited in all environments
BLOCKED_METADATA_IPS = {
    "169.254.169.254",  # AWS/GCP/Azure link-local instance metadata
    "169.254.170.2",    # AWS ECS task metadata
    "fd00:ec2::254",    # AWS IPv6 IMDS
}

BLOCKED_HOSTNAMES = {
    "metadata.google.internal",
    "instance-data",
    "metadata",
}


def validate_target_url(url: str, allow_local_override: bool = False) -> str:
    """
    Validates a service health-check endpoint URL against SSRF vulnerabilities.
    
    Checks:
    - Scheme must be http or https
    - Hostname must be present and well-formed
    - Hostname must not resolve to cloud metadata addresses
    - Hostname must not resolve to private, loopback, link-local, or reserved IP ranges
      unless explicitly permitted in a controlled test environment.
    """
    if not url or not isinstance(url, str):
        raise ValidationException("Target URL cannot be empty.")

    try:
        parsed = urlparse(url.strip())
    except Exception as exc:
        raise ValidationException(f"Invalid URL structure: {str(exc)}")

    # 1. Scheme check
    if parsed.scheme.lower() not in ("http", "https"):
        raise ValidationException(
            f"Unsupported URL scheme '{parsed.scheme}'. Only 'http' and 'https' are permitted."
        )

    # 2. Hostname check
    hostname = parsed.hostname
    if not hostname:
        raise ValidationException("Target URL must specify a valid hostname.")

    hostname_lower = hostname.lower()

    # 3. Block known metadata hostnames unconditionally
    if hostname_lower in BLOCKED_HOSTNAMES:
        raise ValidationException(
            "Access to cloud metadata hostnames is strictly prohibited."
        )

    # 4. Resolve IP address and verify boundaries
    try:
        addr_info = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        # In testing with mock test servers (e.g. testserver), hostname might not resolve via public DNS
        if (settings.ALLOW_LOCAL_TARGETS or allow_local_override) and hostname_lower in ("testserver", "localhost", "127.0.0.1"):
            return url.strip()
        raise ValidationException(f"Could not resolve host '{hostname}'. Target host is unreachable.")

    allow_local = settings.ALLOW_LOCAL_TARGETS or allow_local_override

    for item in addr_info:
        ip_str = item[4][0]

        # Metadata IPs are blocked unconditionally in every environment
        if ip_str in BLOCKED_METADATA_IPS:
            raise ValidationException(
                "Access to cloud metadata IP addresses is strictly prohibited."
            )

        try:
            ip_obj = ipaddress.ip_address(ip_str)
        except ValueError:
            continue

        # If local targets are not allowed, block private and internal networks
        if not allow_local:
            if ip_obj.is_loopback:
                raise ValidationException(
                    "Target URL resolves to a loopback address. Localhost targets are prohibited."
                )
            if ip_obj.is_private:
                raise ValidationException(
                    "Target URL resolves to a private network address (RFC 1918). Internal destinations are prohibited."
                )
            if ip_obj.is_link_local:
                raise ValidationException(
                    "Target URL resolves to a link-local address. Internal destinations are prohibited."
                )
            if ip_obj.is_reserved or ip_obj.is_multicast:
                raise ValidationException(
                    "Target URL resolves to a reserved or multicast address."
                )

    return url.strip()

