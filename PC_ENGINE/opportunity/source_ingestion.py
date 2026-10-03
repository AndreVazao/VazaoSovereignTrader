from __future__ import annotations

import hashlib
import http.client
import ipaddress
import re
import socket
import ssl
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from urllib.parse import unquote, urlsplit


_HOST_LABEL_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")


def _valid_allowlisted_host(host: str) -> bool:
    """Accept explicit DNS hostnames only; reject IP literals and local names."""
    if not host or host != host.lower() or host.endswith(".") or any(c.isspace() for c in host):
        return False
    if "/" in host or ":" in host or "@" in host or "%" in host:
        return False
    try:
        ipaddress.ip_address(host.strip("[]"))
    except ValueError:
        pass
    else:
        return False
    if host == "localhost" or host.endswith((".localhost", ".local", ".internal", ".test", ".invalid")):
        return False
    labels = host.split(".")
    if len(labels) < 2 or any(not _HOST_LABEL_RE.fullmatch(label) for label in labels):
        return False
    return True


def _origin(url: str) -> tuple[str, str, int]:
    """Return the normalized origin for a URL already accepted by the source policy."""
    parsed = urlsplit(url)
    return (parsed.scheme.lower(), parsed.hostname or "", parsed.port or 443)


def _path_matches(path: str, prefix: str) -> bool:
    """Match a path prefix on segment boundaries, never /api against /apix."""
    if prefix == "/":
        return path.startswith("/")
    normalized = prefix.rstrip("/")
    return path == normalized or path.startswith(normalized + "/")


def _validate_public_dns_resolution(host: str, port: int = 443) -> tuple[str, ...]:
    """Fail closed if DNS fails, returns no addresses, or includes any non-global IP."""
    try:
        records = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except OSError as exc:
        raise ValueError("source hostname DNS resolution failed") from exc
    addresses = set()
    for record in records:
        try:
            address = ipaddress.ip_address(record[4][0].split("%", 1)[0])
        except (IndexError, ValueError, TypeError) as exc:
            raise ValueError("source hostname returned an invalid IP address") from exc
        if not address.is_global:
            raise ValueError("source hostname resolves to a non-public IP address")
        addresses.add(str(address))
    if not addresses:
        raise ValueError("source hostname DNS resolution returned no addresses")
    return tuple(sorted(addresses))


class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    """HTTPS connection that dials a validated IP while preserving hostname SNI."""

    def __init__(self, host: str, *, validated_ip: str, **kwargs) -> None:
        super().__init__(host, **kwargs)
        self._validated_ip = validated_ip

    def connect(self) -> None:
        if self._tunnel_host:
            raise OSError("proxy tunneling is not supported for pinned source connections")
        sock = socket.create_connection((self._validated_ip, self.port), self.timeout, self.source_address)
        try:
            self.sock = self._context.wrap_socket(sock, server_hostname=self.host)
        except BaseException:
            sock.close()
            raise


class _PinnedHTTPSHandler(urllib.request.HTTPSHandler):
    """Route HTTPS requests only to addresses validated for the exact request host."""

    def __init__(self, validated_ips_by_host: dict[str, tuple[str, ...]]) -> None:
        super().__init__(context=ssl.create_default_context(), check_hostname=True)
        self._validated_ips_by_host = validated_ips_by_host

    def https_open(self, req):
        parsed = urlsplit(req.full_url)
        host = parsed.hostname
        if not host or parsed.scheme.lower() != "https" or parsed.port not in (None, 443):
            raise urllib.error.URLError("source transport requires an approved HTTPS origin")
        addresses = self._validated_ips_by_host.get(host)
        if not addresses:
            raise urllib.error.URLError("source hostname was not validated")
        validated_ip = addresses[0]

        def connection_factory(connection_host, **kwargs):
            return _PinnedHTTPSConnection(connection_host, validated_ip=validated_ip, **kwargs)

        return self.do_open(connection_factory, req, context=self._context)


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
            if not _valid_allowlisted_host(host):
                raise ValueError("allowed hosts must be explicit public DNS hostnames, not IPs or local names")
        for prefix in self.allowed_path_prefixes:
            if (
                not prefix.startswith("/")
                or "?" in prefix
                or "#" in prefix
                or "\\" in prefix
                or "%" in prefix
                or any(part in (".", "..") for part in prefix.split("/"))
            ):
                raise ValueError("path prefixes must be absolute normalized paths without query, fragment, encoding, or dot segments")

    def allows_url(self, url: str) -> bool:
        try:
            parsed = urlsplit(url)
            host = parsed.hostname or ""
            path = parsed.path or "/"
            decoded_path = unquote(path)
            if (
                parsed.scheme.lower() != "https"
                or parsed.port not in (None, 443)
                or host not in self.allowed_hosts
                or not _valid_allowlisted_host(host)
                or parsed.username is not None
                or parsed.password is not None
                or not parsed.netloc
                or parsed.fragment
                or "\\" in path
                or "%" in path
                or any(part in (".", "..") for part in decoded_path.split("/"))
                or re.search(r"%(?:2f|5c|2e)", path, re.IGNORECASE)
            ):
                return False
            return any(_path_matches(path, prefix) for prefix in self.allowed_path_prefixes)
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
    """Allow only bounded, same-origin redirects that remain inside the source policy."""

    def __init__(self, definition: OfficialSourceDefinition) -> None:
        super().__init__()
        self.definition = definition
        self.redirect_count = 0

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        self.redirect_count += 1
        if self.redirect_count > self.definition.max_redirects:
            raise urllib.error.HTTPError(req.full_url, code, "redirect limit exceeded", headers, fp)

        # Validate both ends before allowing urllib to normalize or follow the target.
        # Same-origin-only redirects mean the original validated/pinned IP remains valid.
        if not self.definition.allows_url(req.full_url):
            raise urllib.error.HTTPError(req.full_url, code, "redirect source is not allowlisted", headers, fp)
        if not self.definition.allows_url(newurl):
            raise urllib.error.HTTPError(req.full_url, code, "redirect target is not allowlisted", headers, fp)
        if _origin(req.full_url) != _origin(newurl):
            raise urllib.error.HTTPError(
                req.full_url, code, "cross-origin redirects require independent revalidation", headers, fp
            )
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
        if now_ms is not None and (isinstance(now_ms, bool) or not isinstance(now_ms, int) or now_ms <= 0):
            raise ValueError("now_ms must be a positive integer")

        parsed_host = urlsplit(url).hostname
        if parsed_host is None:
            raise ValueError("source URL has no hostname")
        validated_ips = _validate_public_dns_resolution(parsed_host, 443)

        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": "VazaoSovereignTrader-Research/1.0",
                "Accept": ", ".join(self._ALLOWED_CONTENT_TYPES),
            },
            method="GET",
        )
        opener = urllib.request.build_opener(
            _AllowlistedRedirectHandler(self.definition),
            _PinnedHTTPSHandler({parsed_host: validated_ips}),
            urllib.request.ProxyHandler({}),
        )
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
            retrieved_at_ms=int(time.time() * 1000) if now_ms is None else now_ms,
            status_code=status_code,
            content_type=content_type,
            content_length=len(body),
            sha256=hashlib.sha256(body).hexdigest(),
            body=body,
        )
