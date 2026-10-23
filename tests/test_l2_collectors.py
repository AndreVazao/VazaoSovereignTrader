from __future__ import annotations

import json
import unittest

from PC_ENGINE.market_events.orderbook_builder import OrderBookBuilder
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

    def test_default_configs_do_not_equate_usdt_with_coinbase_usd(self) -> None:
        usdt_venues = {config.venue for config in default_l2_configs("BTC/USDT")}
        usd_venues = {config.venue for config in default_l2_configs("BTC/USD")}
        self.assertNotIn("coinbase", usdt_venues)
        self.assertIn("coinbase", usd_venues)

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

    def test_okx_books5_update_is_still_a_full_snapshot(self) -> None:
        events = self.collector("okx")._parse(json.dumps({
            "arg": {"channel": "books5"},
            "action": "update",
            "data": [{"ts": "1235", "seqId": 45, "prevSeqId": 44,
                      "bids": [["100.1", "1", "0", "1"]],
                      "asks": [["100.3", "2", "0", "1"]]}],
        }), 9000)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, "snapshot")
        self.assertEqual(events[0].sequence, 45)
        self.assertEqual(events[0].sequence_start, 45)

    def test_okx_rejects_unknown_action(self) -> None:
        with self.assertRaisesRegex(ValueError, "invalid_okx_action"):
            self.collector("okx")._parse(json.dumps({
                "arg": {"channel": "books"},
                "action": "partial",
                "data": [],
            }), 9000)

    def test_coinbase_l2_data_envelope_preserves_sequence_and_timestamp(self) -> None:
        collector = PublicL2WebSocketCollector(
            L2WebSocketConfig("coinbase", "BTC/USD", "wss://example"), lambda _: None)
        events = collector._parse(json.dumps({
            "channel": "l2_data",
            "sequence_num": 42,
            "timestamp": "2026-01-01T00:00:00.000Z",
            "events": [{"type": "update", "product_id": "BTC-USD",
                        "updates": [
                            {"side": "bid", "price_level": "100.0", "new_quantity": "2.0"},
                            {"side": "offer", "price_level": "100.2", "new_quantity": "1.0"}]}],
        }), 9000)
        self.assertEqual(events[0].event_type, "delta")
        self.assertEqual(events[0].sequence, 42)
        self.assertEqual(events[0].exchange_ts_ms, 1767225600000)
        self.assertEqual(len(events[0].bids), 1)
        self.assertEqual(len(events[0].asks), 1)

    def test_coinbase_envelope_with_multiple_items_emits_one_atomic_sequence(self) -> None:
        collector = PublicL2WebSocketCollector(
            L2WebSocketConfig("coinbase", "BTC/USD", "wss://example"), lambda _: None)
        events = collector._parse(json.dumps({
            "channel": "l2_data",
            "sequence_num": 42,
            "timestamp": "2026-01-01T00:00:00.000Z",
            "events": [
                {"type": "update", "product_id": "BTC-USD", "updates": [
                    {"side": "bid", "price_level": "100.0", "new_quantity": "2.0"}]},
                {"type": "update", "product_id": "BTC-USD", "updates": [
                    {"side": "offer", "price_level": "100.2", "new_quantity": "1.0"}]},
            ],
        }), 9000)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].sequence, 42)
        self.assertEqual(events[0].event_type, "delta")
        self.assertEqual(len(events[0].bids), 1)
        self.assertEqual(len(events[0].asks), 1)

    def test_coinbase_atomic_envelope_applies_as_one_contiguous_book_update(self) -> None:
        collector = PublicL2WebSocketCollector(
            L2WebSocketConfig("coinbase", "BTC/USD", "wss://example"), lambda _: None)
        snapshot = collector._parse(json.dumps({
            "channel": "l2_data", "sequence_num": 41,
            "events": [{"type": "snapshot", "product_id": "BTC-USD", "updates": [
                {"side": "bid", "price_level": "100.0", "new_quantity": "2.0"},
                {"side": "offer", "price_level": "101.0", "new_quantity": "3.0"},
            ]}],
        }), 9000)
        delta = collector._parse(json.dumps({
            "channel": "l2_data", "sequence_num": 42,
            "events": [
                {"type": "update", "product_id": "BTC-USD", "updates": [
                    {"side": "bid", "price_level": "100.0", "new_quantity": "4.0"}]},
                {"type": "update", "product_id": "BTC-USD", "updates": [
                    {"side": "offer", "price_level": "101.0", "new_quantity": "0"}]},
            ],
        }), 10000)
        builder = OrderBookBuilder("coinbase", "BTC/USD")
        self.assertIsNotNone(builder.apply(snapshot[0]))
        rebuilt = builder.apply(delta[0])
        self.assertIsNotNone(rebuilt)
        self.assertFalse(builder.stale)
        self.assertEqual(rebuilt.sequence, 42)
        self.assertEqual(rebuilt.bids[0].quantity, 4.0)
        self.assertEqual(rebuilt.asks, ())

    def test_coinbase_envelope_rejects_mixed_snapshot_and_update_items(self) -> None:
        collector = PublicL2WebSocketCollector(
            L2WebSocketConfig("coinbase", "BTC/USD", "wss://example"), lambda _: None)
        with self.assertRaisesRegex(ValueError, "mixed_coinbase_event_types"):
            collector._parse(json.dumps({
                "channel": "l2_data",
                "sequence_num": 42,
                "events": [
                    {"type": "snapshot", "product_id": "BTC-USD", "updates": []},
                    {"type": "update", "product_id": "BTC-USD", "updates": []},
                ],
            }), 9000)

    def test_coinbase_rejects_missing_sequence_and_mismatched_product(self) -> None:
        collector = PublicL2WebSocketCollector(
            L2WebSocketConfig("coinbase", "BTC/USD", "wss://example"), lambda _: None)
        event = {"type": "update", "product_id": "BTC-USD", "updates": []}
        with self.assertRaisesRegex(ValueError, "invalid_coinbase_sequence"):
            collector._parse(json.dumps({"channel": "l2_data", "events": [event]}), 9000)
        with self.assertRaisesRegex(ValueError, "coinbase_product_mismatch"):
            collector._parse(json.dumps({
                "channel": "l2_data", "sequence_num": 43,
                "events": [{"type": "update", "product_id": "ETH-USD", "updates": []}],
            }), 9000)

    def test_coinbase_unknown_side_is_rejected_not_silently_dropped(self) -> None:
        collector = PublicL2WebSocketCollector(
            L2WebSocketConfig("coinbase", "BTC/USD", "wss://example"), lambda _: None)
        with self.assertRaisesRegex(ValueError, "invalid_coinbase_side"):
            collector._parse(json.dumps({
                "channel": "l2_data", "sequence_num": 44,
                "events": [{"type": "update", "product_id": "BTC-USD", "updates": [
                    {"side": "MIDDLE", "price_level": "100", "new_quantity": "1"}]}],
            }), 9000)
