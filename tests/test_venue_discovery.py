from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from PC_ENGINE.radar.venue_discovery import VenueDiscoveryRegistry


class VenueDiscoveryRegistryTests(unittest.TestCase):
    def test_initial_catalogue_is_extensible_and_public_only(self) -> None:
        registry = VenueDiscoveryRegistry()
        ids = {venue.venue_id for venue in registry.list_venues()}
        self.assertTrue({"binance", "coinbase", "okx", "bingx", "bybit", "bitget"} <= ids)
        for venue in registry.list_venues():
            self.assertEqual(venue.private_account_access, "not_configured")
            self.assertEqual(venue.jurisdiction_status, "unknown")
        bitget = registry.get("bitget")
        self.assertFalse(bitget.public_rest)
        self.assertEqual(bitget.lifecycle, "discovered_unverified")
        self.assertTrue(registry.get("binance").public_rest)

    def test_local_candidate_is_added_as_unverified_and_cannot_be_private(self) -> None:
        candidate = [{
            "venue_id": "newvenue",
            "display_name": "New Venue",
            "official_url": "https://example.org",
            "api_docs_url": "https://example.org/api",
            "ccxt_id": "newvenue",
        }]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "venues.json"
            path.write_text(json.dumps(candidate), encoding="utf-8")
            registry = VenueDiscoveryRegistry(path)

        venue = registry.get("newvenue")
        self.assertIsNotNone(venue)
        self.assertEqual(venue.lifecycle, "discovered_unverified")
        self.assertFalse(venue.public_rest)
        self.assertEqual(venue.private_account_access, "not_configured")
        self.assertEqual(venue.source, "local_candidate_file")

    def test_installed_ccxt_venues_are_leads_not_trusted_adapters(self) -> None:
        registry = VenueDiscoveryRegistry()
        leads = registry.ccxt_candidates(["binance", "newvenue", "bad/id", "newvenue", None, 7])
        self.assertEqual(len(leads), 1)
        self.assertEqual(leads[0]["ccxt_id"], "newvenue")
        self.assertEqual(leads[0]["lifecycle"], "discovered_unverified")

    def test_rejects_non_https_and_credentials_in_urls(self) -> None:
        base = {
            "venue_id": "newvenue",
            "display_name": "New Venue",
            "api_docs_url": "https://example.org/api",
            "ccxt_id": None,
        }
        for url in ("http://example.org", "https://user:pass@example.org"):
            with self.subTest(url=url), tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "venues.json"
                path.write_text(json.dumps([{**base, "official_url": url}]), encoding="utf-8")
                with self.assertRaises(ValueError):
                    VenueDiscoveryRegistry(path)

    def test_rejects_duplicate_ids_without_partial_catalogue_mutation(self) -> None:
        item = {
            "venue_id": "newvenue",
            "display_name": "New Venue",
            "official_url": "https://example.org",
            "api_docs_url": "https://example.org/api",
            "ccxt_id": None,
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "venues.json"
            path.write_text(json.dumps([item, item]), encoding="utf-8")
            registry = VenueDiscoveryRegistry.__new__(VenueDiscoveryRegistry)
            registry._venues = {}
            with self.assertRaises(ValueError):
                registry.load_candidates(path)
            self.assertEqual(registry._venues, {})

    def test_missing_candidate_file_is_a_noop(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            registry = VenueDiscoveryRegistry(Path(tmp) / "missing.json")
        self.assertGreaterEqual(len(registry.list_venues()), 6)


if __name__ == "__main__":
    unittest.main()
