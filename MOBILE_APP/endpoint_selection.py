"""Pure endpoint-selection helpers for the Android cockpit.

These helpers do not perform network I/O. They intentionally never retry/replay
commands; callers may use endpoint ordering only for safe connection probes and
read-only requests.
"""
from __future__ import annotations

from urllib.parse import urlsplit


def normalize_endpoint(value: str) -> str:
    """Validate a manually configured private endpoint and normalize its URL."""
    value = (value or "").strip().rstrip("/")
    if not value:
        return ""
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("endpoint_must_be_http_or_https")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("endpoint_must_not_contain_credentials_or_query")
    if parsed.path not in {"", "/"}:
        raise ValueError("endpoint_must_be_base_url")
    return value


def endpoint_candidates(lan_url: str, tailscale_url: str) -> list[str]:
    """Return configured endpoints in LAN-first order, without duplicates."""
    candidates = []
    for value in (lan_url, tailscale_url):
        normalized = normalize_endpoint(value)
        if normalized and normalized not in candidates:
            candidates.append(normalized)
    return candidates


def can_fail_over_automatically(method: str) -> bool:
    """Only idempotent GET probes/reads may be attempted on another route."""
    return (method or "").upper() == "GET"
