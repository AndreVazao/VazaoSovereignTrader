from __future__ import annotations

import json
import unittest

from PC_ENGINE.market_events.l2_collectors import (
    L2WebSocketConfig,
    PublicL2WebSocketCollector,
    default_l2_configs,
)


class L2CollectorTests(unittest.TestCase):
    def test_default_okx_l2_endpoint_uses_tls_443(self) -> None:
        configs = default_l2_configs("BTC/USDT")
        okx = next(config for config in configs if config.venue == "okx")
        self.assertEqual(okx.url, "wss://ws.okx.com/ws/v5/public")
        self.assertNotIn(":8443", okx.url)

    def collector(self, venue: str) -> PublicL2WebSocketCollector:
        return PublicL2WebSocketCollector(
            L2WebSocketConfig(venue, "BTC/USDT", "wss://example"), lambda _: None)

    def test_binance_depth_delta(self) -> None:
        events = self.collector("binance")._parse(json.dumps({
            "e": "depthUpdate", "E": 1234, "U": 10, "u": 12,
            "b": [["100.0", "2.0"]], "a": [["100.2", "3.0"]],
        }), 9000)
        self.assertEqual(events[0].event_type, "delta")
        self.assertEqual(events[0].sequence_start, 10)
        self.assertEqual(events[0].sequence, 12)
        self.assertEqual(events[0].bids[0].quantity, 2.0)

    def test_binance_rejects_malformed_sequence_and_non_finite_level(self) -> None:
        payloads = (
            {"e": "depthUpdate", "E": 1, "U": -1, "u": 2, "b": [], "a": []},
            {"e": "depthUpdate", "E": 1, "U": 3, "u": 2, "b": [], "a": []},
            {"e": "depthUpdate", "E": 1, "U": 1, "u": 1, "b": [["nan", "1"]], "a": []},
            {"e": "depthUpdate", "E": 1, "U": 1, "u": 1, "b": [["100", "inf"]], "a": []},
            {"e": "depthUpdate", "E": 1, "U": "1", "u": 1, "b": [], "a": []},
        )
        for payload in payloads:
            with self.subTest(payload=payload):
                with self.assertRaises(ValueError):
                    self.collector("binance")._parse(json.dumps(payload), 9000)

    def test_malformed_message_is_counted_without_raw_payload(self) -> None:
        collector = self.collector("binance")
        collector.process_message('{"e":"depthUpdate","U":-1,"u":2,"b":[],"a":[]}')
        health = collector.health_snapshot()
        self.assertEqual(health["parse_errors"], 1)
        self.assertEqual(health["last_parse_error"], "ValueError")
        self.assertNotIn("depthUpdate", str(health))

    def test_raw_persistence_error_does_not_escape_message_callback(self) -> None:
        collector = PublicL2WebSocketCollector(
            L2WebSocketConfig("binance", "BTC/USDT", "wss://example"),
            lambda _event: (_ for _ in ()).throw(OSError("private path detail")),
        )
        collector.process_message(json.dumps({
            "e": "depthUpdate", "E": 1, "U": 1, "u": 1,
            "b": [["100", "1"]], "a": [["101", "1"]],
        }))
        health = collector.health_snapshot()
        self.assertEqual(health["raw_callback_errors"], 1)
        self.assertEqual(health["last_raw_callback_error"], "OSError")
        self.assertNotIn("private path detail", str(health))

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

    def test_coinbase_unknown_side_is_rejected_not_silently_dropped(self) -> None:
        with self.assertRaises(ValueError):
            self.collector("coinbase")._parse(json.dumps({
                "channel": "level2",
                "events": [{"type": "update", "updates": [
                    {"side": "MIDDLE", "price_level": "100", "new_quantity": "1"}]}],
            }), 9000)
