from __future__ import annotations

import unittest

from PC_ENGINE.radar.collection_routing import reviewed_stream_venues
from PC_ENGINE.radar.venue_discovery import VenueDiscoveryRegistry


class CollectionRoutingTests(unittest.TestCase):
    def test_defaults_to_reviewed_native_stream_venues(self) -> None:
        registry = VenueDiscoveryRegistry()
        result = reviewed_stream_venues(
            registry, {"binance", "okx", "coinbase", "bingx"}
        )
        self.assertEqual(result, ["binance", "coinbase", "okx"])

    def test_explicit_unverified_or_unsupported_venue_is_rejected(self) -> None:
        registry = VenueDiscoveryRegistry()
        for requested in (["bitget"], ["bingx"], ["unknown"]):
            with self.subTest(requested=requested):
                with self.assertRaisesRegex(ValueError, "venues_not_reviewed"):
                    reviewed_stream_venues(
                        registry, {"binance", "okx", "coinbase", "bingx"}, requested
                    )

    def test_explicit_supported_venue_is_preserved_in_requested_order(self) -> None:
        registry = VenueDiscoveryRegistry()
        self.assertEqual(
            reviewed_stream_venues(registry, {"binance", "okx", "coinbase"}, ["okx", "binance", "okx"]),
            ["okx", "binance"],
        )


if __name__ == "__main__":
    unittest.main()
