from __future__ import annotations

import hashlib
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from urllib.parse import urlsplit


@dataclass(frozen=True)
class OfficialSourceDefinition:
    """An explicitly approved public source. Hosts and paths are exact policy inputs."""

    source_id: str
    allowed_hosts: tuple[str, ...]
    allowed_path_prefixes: tuple[str, ...]
    max_bytes: int = 512_000
    timeout_seconds: float = 8.0
    max_redirects: int = 3

    def __post_init__(self) -> None:
        if not self.source_id.strip():
            raise ValueError("source_id is required")
        if not self.allowed_hosts or not self.allowed_path_prefixes:
            raise ValueError("host and path allowlists are required")
        if self.max_bytes < 1 or self.timeout_seconds <= 0 or self.max_redirects < 0:
            raise ValueError("fetch limits must be positive (redirect count may be zero)")
        for host in self.allowed_hosts:
            if (
                not host
                or host != host.lower()
                or "/" in host
                or ":" in host
                or host.endswith(".")
                or any(char.isspace() for char in host)
            ):
                raise ValueError("allowed hosts must be lowercase hostnames without ports")
        for prefix in self.allowed_path_prefixes:
            if not prefix.startswith("/") or "?" in prefix or "#" in prefix:
                raise ValueError("allowed path prefixes must be absolute paths without query or fragment")

    def allows_url(self, url: str) -> bool:
        try:
            parsed = urlsplit(url)
            host = parsed.hostname or ""
            return (
                parsed.scheme == "https"
                and parsed.port in (None, 443)
                and host in self.allowed_hosts
                and parsed.username is None
                and parsed.password is None
                and not parsed.fragment
                and any(parsed.path.startswith(prefix) for prefix in self.allowed_path_prefixes)
            )
        except (TypeError, ValueError):
            return False


@dataclass(frozen=True)
class OfficialSourceSnapshot:
    source_id: str
    requested_url: str
    final_url: str
    retrieved_at_ms: int
    status_code: int
    content_type: str
    content_length: int
    sha256: str
    body: bytes


class _AllowlistedRedirectHandler(urllib.request.HTTPRedirectHandler):
    def __init__(self, definition: OfficialSourceDefinition) -> None:
        super().__init__()
        self.definition = definition
        self.redirect_count = 0

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        self.redirect_count += 1
        if self.redirect_count > self.definition.max_redirects:
            raise urllib.error.HTTPError(req.full_url, code, "redirect limit exceeded", headers, fp)
        if not self.definition.allows_url(newurl):
            raise urllib.error.HTTPError(req.full_url, code, "redirect target is not allowlisted", headers, fp)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class OfficialSourceFetcher:
    """Bounded, read-only public-source fetcher; never accesses authenticated accounts."""

    _ALLOWED_CONTENT_TYPES = (
        "text/html",
        "text/plain",
        "application/json",
        "application/xml",
        "text/xml",
    )

    def __init__(self, definition: OfficialSourceDefinition) -> None:
        self.definition = definition

    def fetch(self, url: str, *, now_ms: int | None = None) -> OfficialSourceSnapshot:
        if not self.definition.allows_url(url):
            raise ValueError("URL is outside the configured HTTPS host/path allowlist")

        request = urllib.request.Request(
            url,
            headers={"User-Agent": "VazaoSovereignTrader-Research/1.0", "Accept": ", ".join(self._ALLOWED_CONTENT_TYPES)},
            method="GET",
        )
        opener = urllib.request.build_opener(_AllowlistedRedirectHandler(self.definition))
        with opener.open(request, timeout=self.definition.timeout_seconds) as response:
            final_url = response.geturl()
            if not self.definition.allows_url(final_url):
                raise ValueError("final URL is outside the configured HTTPS host/path allowlist")
            status_code = int(getattr(response, "status", response.getcode()))
            if status_code < 200 or status_code >= 300:
                raise ValueError(f"source returned non-success status: {status_code}")
            content_type = str(response.headers.get("Content-Type", "")).split(";", 1)[0].strip().lower()
            if content_type not in self._ALLOWED_CONTENT_TYPES:
                raise ValueError("source content type is not allowlisted")
            raw_length = response.headers.get("Content-Length")
            if raw_length is not None:
                try:
                    declared_length = int(raw_length)
                except (TypeError, ValueError) as exc:
                    raise ValueError("invalid Content-Length header") from exc
                if declared_length < 0:
                    raise ValueError("invalid Content-Length header")
                if declared_length > self.definition.max_bytes:
                    raise ValueError("source response exceeds configured byte limit")
            body = response.read(self.definition.max_bytes + 1)
            if len(body) > self.definition.max_bytes:
                raise ValueError("source response exceeds configured byte limit")

        return OfficialSourceSnapshot(
            source_id=self.definition.source_id,
            requested_url=url,
            final_url=final_url,
            retrieved_at_ms=int(time.time() * 1000) if now_ms is None else int(now_ms),
            status_code=status_code,
            content_type=content_type,
            content_length=len(body),
            sha256=hashlib.sha256(body).hexdigest(),
            body=body,
        )
