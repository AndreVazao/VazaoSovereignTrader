from __future__ import annotations

import hashlib
import ipaddress
import re
from dataclasses import dataclass
from urllib.parse import urlsplit, urlunsplit


_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _origin(url: str) -> tuple[str, str, int]:
    """Return a normalized HTTPS origin or reject ambiguous/non-web URLs."""
    try:
        parsed = urlsplit(url.strip())
        host = parsed.hostname
        port = parsed.port
    except (TypeError, ValueError) as exc:
        raise ValueError("source URL is malformed") from exc
    if parsed.scheme.lower() != "https" or not host:
        raise ValueError("source URL must use HTTPS and include a hostname")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("source URL must not embed credentials")
    if parsed.fragment:
        raise ValueError("source URL fragments are not accepted")
    if port not in (None, 443):
        raise ValueError("source URL must use the standard HTTPS port")
    normalized_host = host.rstrip(".").lower()
    if not normalized_host or ".." in normalized_host:
        raise ValueError("source hostname is malformed")
    try:
        ipaddress.ip_address(normalized_host.strip("[]"))
    except ValueError:
        pass
    else:
        raise ValueError("IP-literal source hosts are not accepted")
    return ("https", normalized_host, 443)


@dataclass(frozen=True)
class OfficialSourcePolicy:
    """Explicit exact-host allowlist; no network access or implicit trust."""

    allowed_hosts: frozenset[str]

    def __post_init__(self) -> None:
        normalized: set[str] = set()
        for host in self.allowed_hosts:
            candidate = host.strip().rstrip(".").lower()
            if not candidate or "/" in candidate or ":" in candidate or "@" in candidate:
                raise ValueError("allowlist entries must be bare exact hostnames")
            try:
                ipaddress.ip_address(candidate.strip("[]"))
            except ValueError:
                pass
            else:
                raise ValueError("IP-literal allowlist entries are not accepted")
            normalized.add(candidate)
        object.__setattr__(self, "allowed_hosts", frozenset(normalized))

    def validate_url(self, url: str) -> str:
        origin = _origin(url)
        if origin[1] not in self.allowed_hosts:
            raise ValueError("source hostname is not allowlisted")
        parsed = urlsplit(url.strip())
        # Preserve path/query while canonicalizing the origin.
        path = parsed.path or "/"
        return urlunsplit(("https", origin[1], path, parsed.query, ""))

    def validate_observation(
        self,
        *,
        source_url: str,
        observed_at_ms: int,
        source_captured_at_ms: int,
        evidence_sha256: str,
        final_url: str | None = None,
        now_ms: int,
    ) -> "SourceObservation":
        canonical_source = self.validate_url(source_url)
        if isinstance(observed_at_ms, bool) or not isinstance(observed_at_ms, int) or observed_at_ms <= 0:
            raise ValueError("observed_at_ms must be a positive integer")
        if isinstance(source_captured_at_ms, bool) or not isinstance(source_captured_at_ms, int) or source_captured_at_ms <= 0:
            raise ValueError("source_captured_at_ms must be a positive integer")
        if isinstance(now_ms, bool) or not isinstance(now_ms, int) or now_ms <= 0:
            raise ValueError("now_ms must be a positive integer")
        if observed_at_ms > now_ms + 300_000 or source_captured_at_ms > now_ms + 300_000:
            raise ValueError("observation timestamps cannot be materially in the future")
        if source_captured_at_ms > observed_at_ms + 300_000:
            raise ValueError("source capture time cannot materially follow observation time")
        if not _SHA256_RE.fullmatch(evidence_sha256):
            raise ValueError("evidence_sha256 must be a lowercase SHA-256 hex digest")

        if final_url is not None:
            canonical_final = self.validate_url(final_url)
            if _origin(canonical_final) != _origin(canonical_source):
                raise ValueError("cross-origin redirects require independent revalidation")
        else:
            canonical_final = None

        return SourceObservation(
            source_url=canonical_source,
            observed_at_ms=observed_at_ms,
            source_captured_at_ms=source_captured_at_ms,
            evidence_sha256=evidence_sha256,
            final_url=canonical_final,
        )


@dataclass(frozen=True)
class SourceObservation:
    """Metadata-only proof of a source observation; never stores page contents."""

    source_url: str
    observed_at_ms: int
    source_captured_at_ms: int
    evidence_sha256: str
    final_url: str | None = None

    @property
    def fingerprint(self) -> str:
        material = "\n".join(
            (
                self.source_url,
                str(self.source_captured_at_ms),
                self.evidence_sha256,
            )
        )
        return hashlib.sha256(material.encode("utf-8")).hexdigest()
