from __future__ import annotations

import hashlib
import unittest
from unittest.mock import MagicMock, patch

from PC_ENGINE.opportunity.source_ingestion import (
    OfficialSourceDefinition,
    OfficialSourceFetcher,
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
    def test_url_allowlist_requires_https_exact_host_and_approved_path(self):
        item = definition()
        self.assertTrue(item.allows_url("https://support.example.com/en/faq/topic"))
        self.assertFalse(item.allows_url("http://support.example.com/en/faq/topic"))
        self.assertFalse(item.allows_url("https://evil.example.com/en/faq/topic"))
        self.assertFalse(item.allows_url("https://support.example.com.evil.test/en/faq/topic"))
        self.assertFalse(item.allows_url("https://support.example.com/account/private"))
        self.assertFalse(item.allows_url("https://user:pass@support.example.com/en/faq/topic"))
        self.assertFalse(item.allows_url("https://support.example.com/en/faq/topic#fragment"))

    def test_fetch_rejects_url_before_network_call(self):
        fetcher = OfficialSourceFetcher(definition())
        with patch("PC_ENGINE.opportunity.source_ingestion.urllib.request.build_opener") as build:
            with self.assertRaisesRegex(ValueError, "allowlist"):
                fetcher.fetch("https://support.example.com/account/private")
            build.assert_not_called()

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


if __name__ == "__main__":
    unittest.main()
