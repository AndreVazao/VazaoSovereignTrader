from __future__ import annotations

import tempfile
import unittest

from PC_ENGINE.radar.market_radar import LeadLagObservation, MarketRadar, VenueSnapshot


class MarketRadarTests(unittest.TestCase):
    def test_detects_candidate_lead_lag(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            radar = MarketRadar.__new__(MarketRadar)
            radar.previous = {
                ("binance", "BTC/USDT"): VenueSnapshot("binance", "BTC/USDT", 100.0, 99.9, 100.1, 1000, 1000, 1100, 100),
                ("okx", "BTC/USDT"): VenueSnapshot("okx", "BTC/USDT", 100.0, 99.9, 100.1, 1000, 1000, 1100, 100),
            }
            current = [
                VenueSnapshot("okx", "BTC/USDT", 100.08, 100.0, 100.1, 1100, 2000, 2000, 0),
                VenueSnapshot("binance", "BTC/USDT", 100.07, 100.0, 100.1, 1100, 2001, 2001, 0),
            ]
            events = radar._detect_leads(current)
            self.assertEqual(len(events), 1)
            self.assertIsInstance(events[0], LeadLagObservation)
            self.assertEqual(events[0].leader, "okx")
            self.assertEqual(events[0].follower, "binance")
            self.assertEqual(events[0].direction, "UP")
            self.assertEqual(events[0].lag_ms, 1)

    def test_pressure_is_normalized(self) -> None:
        radar = MarketRadar.__new__(MarketRadar)
        radar.previous = {
            ("binance", "BTC/USDT"): VenueSnapshot("binance", "BTC/USDT", 100.0, 0, 0, 0, None, 0, None),
        }
        snapshots = [VenueSnapshot("binance", "BTC/USDT", 100.1, 0, 0, 0, None, 1, None)]
        pressure = radar._pressure_from_previous(snapshots)
        self.assertGreater(pressure["BTC/USDT"], 0)
        self.assertLessEqual(pressure["BTC/USDT"], 1)


if __name__ == "__main__":
    unittest.main()
