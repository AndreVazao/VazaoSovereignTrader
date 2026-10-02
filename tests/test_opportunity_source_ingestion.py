from __future__ import annotations

import hashlib
import socket
import unittest
from unittest.mock import MagicMock, patch

from PC_ENGINE.opportunity.source_ingestion import (
    OfficialSourceDefinition,
    OfficialSourceFetcher,
    _AllowlistedRedirectHandler,
    _PinnedHTTPSConnection,
)


def definition(**overrides) -> OfficialSourceDefinition:
    values = {
        "source_id": "example-official-faq",
        "allowed_hosts": ("support.example.com",),
        "allowed_path_prefixes": ("/en/faq/", "/pt/faq/"),
        "max_bytes": 64,
        "timeout_seconds": 1.5,
        "max_redirects": 2,
    }
    values.update(overrides)
    return OfficialSourceDefinition(**values)


class OfficialSourceIngestionTests(unittest.TestCase):
    def test_pinned_connection_dials_validated_ip_and_preserves_tls_hostname(self):
        connection = _PinnedHTTPSConnection("support.example.com", validated_ip="93.184.216.34", timeout=1.5)
        raw_socket = MagicMock()
        tls_socket = MagicMock()
        with patch("PC_ENGINE.opportunity.source_ingestion.socket.create_connection", return_value=raw_socket) as create:
            with patch.object(connection._context, "wrap_socket", return_value=tls_socket) as wrap:
                connection.connect()
        create.assert_called_once_with(("93.184.216.34", 443), 1.5, None)
        wrap.assert_called_once_with(raw_socket, server_hostname="support.example.com")
        self.assertIs(connection.sock, tls_socket)

    def test_pinned_connection_does_not_follow_proxy_tunnel(self):
        connection = _PinnedHTTPSConnection("support.example.com", validated_ip="93.184.216.34")
        connection.set_tunnel("proxy.example.com")
        with self.assertRaisesRegex(OSError, "proxy tunneling is not supported"):
            connection.connect()

    def setUp(self):
        self.dns_patcher = patch(
            "PC_ENGINE.opportunity.source_ingestion.socket.getaddrinfo",
            return_value=[(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443))],
        )
        self.dns_patcher.start()
        self.addCleanup(self.dns_patcher.stop)

    def test_dns_preflight_rejects_private_address_before_network_call(self):
        fetcher = OfficialSourceFetcher(definition())
        private_record = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 443))]
        with patch("PC_ENGINE.opportunity.source_ingestion.socket.getaddrinfo", return_value=private_record):
            with patch("PC_ENGINE.opportunity.source_ingestion.urllib.request.build_opener") as build:
                with self.assertRaisesRegex(ValueError, "non-public IP"):
                    fetcher.fetch("https://support.example.com/en/faq/topic")
                build.assert_not_called()

    def test_dns_preflight_rejects_mixed_public_and_private_answers(self):
        fetcher = OfficialSourceFetcher(definition())
        records = [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443)),
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.0.0.8", 443)),
        ]
        with patch("PC_ENGINE.opportunity.source_ingestion.socket.getaddrinfo", return_value=records):
            with patch("PC_ENGINE.opportunity.source_ingestion.urllib.request.build_opener") as build:
                with self.assertRaisesRegex(ValueError, "non-public IP"):
                    fetcher.fetch("https://support.example.com/en/faq/topic")
                build.assert_not_called()

    def test_dns_preflight_fails_closed_on_resolution_error(self):
        fetcher = OfficialSourceFetcher(definition())
        with patch("PC_ENGINE.opportunity.source_ingestion.socket.getaddrinfo", side_effect=socket.gaierror("no answer")):
            with patch("PC_ENGINE.opportunity.source_ingestion.urllib.request.build_opener") as build:
                with self.assertRaisesRegex(ValueError, "DNS resolution failed"):
                    fetcher.fetch("https://support.example.com/en/faq/topic")
                build.assert_not_called()
    def test_url_allowlist_requires_https_exact_host_and_approved_path(self):
        item = definition()
        self.assertTrue(item.allows_url("https://support.example.com/en/faq/topic"))
        self.assertFalse(item.allows_url("http://support.example.com/en/faq/topic"))
        self.assertFalse(item.allows_url("https://evil.example.com/en/faq/topic"))
        self.assertFalse(item.allows_url("https://support.example.com.evil.test/en/faq/topic"))
        self.assertFalse(item.allows_url("https://support.example.com/account/private"))
        self.assertFalse(item.allows_url("https://user:pass@support.example.com/en/faq/topic"))
        self.assertFalse(item.allows_url("https://support.example.com/en/faq/topic#fragment"))
        self.assertFalse(item.allows_url("https://support.example.com:8443/en/faq/topic"))

    def test_configuration_rejects_ip_literal_and_local_hosts(self):
        for host in ("127.0.0.1", "192.168.1.1", "::1", "localhost", "api.localhost",
                     "service.internal", "singlelabel"):
            with self.subTest(host=host):
                with self.assertRaisesRegex(ValueError, "public DNS hostnames"):
                    definition(allowed_hosts=(host,))

    def test_configuration_rejects_malformed_hostnames(self):
        for host in ("Support.example.com", "support.example.com.", "bad host.example",
                     "support..example.com", "support.example.com:443"):
            with self.subTest(host=host):
                with self.assertRaisesRegex(ValueError, "public DNS hostnames"):
                    definition(allowed_hosts=(host,))

    def test_path_prefix_matching_respects_segment_boundary(self):
        item = definition(allowed_path_prefixes=("/api",))
        self.assertTrue(item.allows_url("https://support.example.com/api"))
        self.assertTrue(item.allows_url("https://support.example.com/api/v1"))
        self.assertFalse(item.allows_url("https://support.example.com/apix"))
        self.assertFalse(item.allows_url("https://support.example.com/api-v2"))

    def test_encoded_path_traversal_and_separators_are_rejected(self):
        item = definition(allowed_path_prefixes=("/en/faq/",))
        for path in (
            "/en/faq/%2e%2e/private",
            "/en/faq/%2fprivate",
            "/en/faq/%5cprivate",
            "/en/faq/../private",
            "/en/faq/..%2fprivate",
            "/en/faq/%252e%252e/private",
        ):
            with self.subTest(path=path):
                self.assertFalse(item.allows_url("https://support.example.com" + path))

    def test_fetch_rejects_url_before_network_call(self):
        fetcher = OfficialSourceFetcher(definition())
        with patch("PC_ENGINE.opportunity.source_ingestion.urllib.request.build_opener") as build:
            with self.assertRaisesRegex(ValueError, "allowlist"):
                fetcher.fetch("https://support.example.com/account/private")
            build.assert_not_called()

    def test_fetch_rejects_invalid_now_ms_before_network_call(self):
        fetcher = OfficialSourceFetcher(definition())
        for value in (-1, 0, True, False, "1234", 1.5):
            with self.subTest(now_ms=value):
                with patch("PC_ENGINE.opportunity.source_ingestion.urllib.request.build_opener") as build:
                    with self.assertRaisesRegex(ValueError, "positive integer"):
                        fetcher.fetch("https://support.example.com/en/faq/topic", now_ms=value)
                    build.assert_not_called()

    def test_redirect_handler_rejects_unapproved_host(self):
        item = definition()
        handler = _AllowlistedRedirectHandler(item)
        request = __import__("urllib.request", fromlist=["Request"]).Request(
            "https://support.example.com/en/faq/topic"
        )
        with self.assertRaisesRegex(Exception, "not allowlisted"):
            handler.redirect_request(
                request, None, 302, "Found", {}, "https://evil.example.com/en/faq/topic"
            )

    def test_redirect_handler_allows_same_origin_approved_path(self):
        item = definition()
        handler = _AllowlistedRedirectHandler(item)
        request = __import__("urllib.request", fromlist=["Request"]).Request(
            "https://support.example.com/en/faq/topic"
        )
        redirected = handler.redirect_request(
            request, None, 302, "Found", {}, "https://support.example.com/en/faq/next"
        )
        self.assertEqual(redirected.full_url, "https://support.example.com/en/faq/next")

    def test_redirect_handler_rejects_cross_origin_even_when_target_host_is_allowlisted(self):
        item = definition(allowed_hosts=("support.example.com", "cdn.example.com"))
        handler = _AllowlistedRedirectHandler(item)
        request = __import__("urllib.request", fromlist=["Request"]).Request(
            "https://support.example.com/en/faq/topic"
        )
        with self.assertRaisesRegex(Exception, "cross-origin redirects require independent revalidation"):
            handler.redirect_request(
                request, None, 302, "Found", {}, "https://cdn.example.com/en/faq/topic"
            )

    def test_redirect_handler_enforces_redirect_limit(self):
        item = definition(max_redirects=0)
        handler = _AllowlistedRedirectHandler(item)
        request = __import__("urllib.request", fromlist=["Request"]).Request(
            "https://support.example.com/en/faq/topic"
        )
        with self.assertRaisesRegex(Exception, "redirect limit"):
            handler.redirect_request(
                request, None, 302, "Found", {}, "https://support.example.com/en/faq/next"
            )

    def test_fetch_records_hash_timestamp_and_bounded_metadata(self):
        body = b'{"campaign":"sample"}'
        response = MagicMock()
        response.__enter__.return_value = response
        response.geturl.return_value = "https://support.example.com/en/faq/topic"
        response.status = 200
        response.getcode.return_value = 200
        response.headers = {"Content-Type": "application/json; charset=utf-8", "Content-Length": str(len(body))}
        response.read.return_value = body
        opener = MagicMock()
        opener.open.return_value = response
        with patch("PC_ENGINE.opportunity.source_ingestion.urllib.request.build_opener", return_value=opener):
            snapshot = OfficialSourceFetcher(definition()).fetch(
                "https://support.example.com/en/faq/topic", now_ms=1234
            )
        self.assertEqual(snapshot.retrieved_at_ms, 1234)
        self.assertEqual(snapshot.sha256, hashlib.sha256(body).hexdigest())
        self.assertEqual(snapshot.content_length, len(body))
        self.assertEqual(snapshot.body, body)
        opener.open.assert_called_once()
        self.assertEqual(opener.open.call_args.kwargs["timeout"], 1.5)

    def test_fetch_rejects_oversized_declared_content_length(self):
        response = MagicMock()
        response.__enter__.return_value = response
        response.geturl.return_value = "https://support.example.com/en/faq/topic"
        response.status = 200
        response.getcode.return_value = 200
        response.headers = {"Content-Type": "text/plain", "Content-Length": "999"}
        opener = MagicMock()
        opener.open.return_value = response
        with patch("PC_ENGINE.opportunity.source_ingestion.urllib.request.build_opener", return_value=opener):
            with self.assertRaisesRegex(ValueError, "byte limit"):
                OfficialSourceFetcher(definition()).fetch("https://support.example.com/en/faq/topic")
        response.read.assert_not_called()

    def test_fetch_rejects_oversized_stream_without_content_length(self):
        response = MagicMock()
        response.__enter__.return_value = response
        response.geturl.return_value = "https://support.example.com/en/faq/topic"
        response.status = 200
        response.getcode.return_value = 200
        response.headers = {"Content-Type": "text/plain"}
        response.read.return_value = b"x" * 65
        opener = MagicMock()
        opener.open.return_value = response
        with patch("PC_ENGINE.opportunity.source_ingestion.urllib.request.build_opener", return_value=opener):
            with self.assertRaisesRegex(ValueError, "byte limit"):
                OfficialSourceFetcher(definition()).fetch("https://support.example.com/en/faq/topic")

    def test_fetch_rejects_unexpected_content_type(self):
        response = MagicMock()
        response.__enter__.return_value = response
        response.geturl.return_value = "https://support.example.com/en/faq/topic"
        response.status = 200
        response.getcode.return_value = 200
        response.headers = {"Content-Type": "application/octet-stream"}
        opener = MagicMock()
        opener.open.return_value = response
        with patch("PC_ENGINE.opportunity.source_ingestion.urllib.request.build_opener", return_value=opener):
            with self.assertRaisesRegex(ValueError, "content type"):
                OfficialSourceFetcher(definition()).fetch("https://support.example.com/en/faq/topic")

    def test_definition_rejects_unbounded_configuration(self):
        with self.assertRaisesRegex(ValueError, "allowlists"):
            definition(allowed_hosts=())
        with self.assertRaisesRegex(ValueError, "fetch limits"):
            definition(max_bytes=0)
        with self.assertRaisesRegex(ValueError, "path prefixes"):
            definition(allowed_path_prefixes=("",))
        with self.assertRaisesRegex(ValueError, "path prefixes"):
            definition(allowed_path_prefixes=("/api/%2e%2e/",))
        with self.assertRaisesRegex(ValueError, "path prefixes"):
            definition(allowed_path_prefixes=("/api/../",))


if __name__ == "__main__":
    unittest.main()
