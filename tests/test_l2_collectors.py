from __future__ import annotations

import json
import unittest

from PC_ENGINE.market_events.l2_collectors import L2WebSocketConfig, PublicL2WebSocketCollector


class L2CollectorTests(unittest.TestCase):
    def collector(self, venue: str) -> PublicL2WebSocketCollector:
        return PublicL2WebSocketCollector(
            L2WebSocketConfig(venue, "BTC/USDT", "wss://example"), lambda _: None)

    def test_binance_depth_delta(self) -> None:
        events = self.collector("binance")._parse(json.dumps({
            "e": "depthUpdate", "E": 1234, "U": 10, "u": 12,
            "b": [["100.0", "2.0"]], "a": [["100.2", "3.0"]],
        }), 9000)
        self.assertEqual(events[0].event_type, "delta")
        self.assertEqual(events[0].sequence, 12)
        self.assertEqual(events[0].bids[0].quantity, 2.0)

    def test_okx_snapshot(self) -> None:
        events = self.collector("okx")._parse(json.dumps({
            "arg": {"channel": "books5"}, "action": "snapshot",
            "data": [{"ts": "1234", "seqId": 44,
                      "bids": [["100.0", "2", "0", "3"]],
                      "asks": [["100.2", "4", "0", "2"]]}],
        }), 9000)
        self.assertEqual(events[0].event_type, "snapshot")
        self.assertEqual(events[0].sequence, 44)
        self.assertEqual(events[0].asks[0].quantity, 4.0)

    def test_coinbase_level2(self) -> None:
        events = self.collector("coinbase")._parse(json.dumps({
            "channel": "level2",
            "events": [{"type": "update", "event_time": "2026-01-01T00:00:00.000Z",
                        "updates": [
                            {"side": "bid", "price_level": "100.0", "new_quantity": "2.0"},
                            {"side": "offer", "price_level": "100.2", "new_quantity": "1.0"}]}],
        }), 9000)
        self.assertEqual(events[0].event_type, "delta")
        self.assertEqual(len(events[0].bids), 1)
        self.assertEqual(len(events[0].asks), 1)
