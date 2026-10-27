from __future__ import annotations

import json
import unittest
from dataclasses import dataclass

from PC_ENGINE.market_events.orderbook_builder import OrderBookBuilder
from PC_ENGINE.market_events.l2_collectors import (
    L2WebSocketConfig,
    PublicL2WebSocketCollector,
    default_l2_configs,
)


class L2CollectorTests(unittest.TestCase):
    def test_synchronized_book_persistence_routes_by_venue_and_fails_closed(self) -> None:
        from pathlib import Path
        from PC_ENGINE.tools.run_l2_market_data_collector import (
            persist_synchronized_book,
            synchronized_book_path,
        )

        @dataclass
        class View:
            venue: str
            status: str
            eligible: bool = True

        root = Path("data")
        outputs = {venue: synchronized_book_path(root, venue)
                   for venue in ("binance", "coinbase", "okx")}
        written = []
        for venue in outputs:
            persist_synchronized_book(
                View(venue=venue, status="SYNCED"), outputs,
                lambda path, payload: written.append((path, payload)),
            )
        self.assertEqual([path.name for path, _ in written], [
            "binance_synchronized_orderbook_views.jsonl",
            "coinbase_synchronized_orderbook_views.jsonl",
            "okx_synchronized_orderbook_views.jsonl",
        ])
        self.assertTrue(all(payload["status"] == "SYNCED" for _, payload in written))
        with self.assertRaisesRegex(ValueError, "unsupported_synchronized_book_venue"):
            persist_synchronized_book(
                View(venue="unknown", status="SYNCED"), outputs,
                lambda _path, _payload: self.fail("unsupported venue must not be written"),
            )

    def test_l2_runner_wires_synchronized_views_for_all_supported_venues(self) -> None:
        from PC_ENGINE.tools.run_l2_market_data_collector import build_collector

        for venue in ("binance", "coinbase", "okx"):
            with self.subTest(venue=venue):
                symbol = "BTC/USD" if venue == "coinbase" else "BTC/USDT"
                config = next(
                    config for config in default_l2_configs(symbol)
                    if config.venue == venue
                )
                collector = build_collector(config, lambda _event: None, lambda _view: None)
                self.assertIsNotNone(
                    collector._sync if venue == "binance"
                    else collector._coinbase_sync if venue == "coinbase"
                    else collector._okx_sync
                )
                collector.stop()

    def test_l2_runner_uses_separate_output_files_per_venue(self) -> None:
        from pathlib import Path
        from PC_ENGINE.tools.run_l2_market_data_collector import synchronized_book_path

        root = Path("some-data-dir")
        self.assertEqual(
            synchronized_book_path(root, "binance"),
            root / "binance_synchronized_orderbook_views.jsonl",
        )
        self.assertEqual(
            synchronized_book_path(root, "coinbase"),
            root / "coinbase_synchronized_orderbook_views.jsonl",
        )
        self.assertEqual(
            synchronized_book_path(root, "okx"),
            root / "okx_synchronized_orderbook_views.jsonl",
        )
        with self.assertRaisesRegex(ValueError, "unsupported_synchronized_book_venue"):
            synchronized_book_path(root, "unknown")

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

    def test_coinbase_malformed_depth_message_clears_previous_eligible_book(self) -> None:
        views = []
        collector = PublicL2WebSocketCollector(
            L2WebSocketConfig("coinbase", "BTC/USD", "wss://example"),
            lambda _event: None,
            on_book=views.append,
        )
        collector.process_message(json.dumps({
            "channel": "l2_data",
            "sequence_num": 41,
            "events": [{"type": "snapshot", "product_id": "BTC-USD", "updates": [
                {"side": "bid", "price_level": "100", "new_quantity": "2"},
                {"side": "offer", "price_level": "101", "new_quantity": "3"},
            ]}],
        }))
        self.assertTrue(views[-1].eligible)

        # A depth envelope without a valid sequence is not safely ignorable:
        # the previous book must become ineligible immediately.
        collector.process_message(json.dumps({
            "channel": "l2_data",
            "sequence_num": "invalid",
            "events": [{"type": "update", "product_id": "BTC-USD", "updates": []}],
        }))
        self.assertFalse(views[-1].eligible)
        self.assertEqual(views[-1].reason, "parse_error")
        self.assertEqual(views[-1].bids, ())
        self.assertEqual(views[-1].asks, ())
        self.assertEqual(collector.health_snapshot()["parse_errors"], 1)

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
            "arg": {"instId": "BTC-USDT", "channel": "books5"}, "action": "snapshot",
            "data": [{"ts": "1234", "seqId": 44,
                      "bids": [["100.0", "2", "0", "3"]],
                      "asks": [["100.2", "4", "0", "2"]]}],
        }), 9000)
        self.assertEqual(events[0].event_type, "snapshot")
        self.assertEqual(events[0].sequence, 44)
        self.assertEqual(events[0].asks[0].quantity, 4.0)

    def test_okx_books5_update_is_still_a_full_snapshot(self) -> None:
        events = self.collector("okx")._parse(json.dumps({
            "arg": {"instId": "BTC-USDT", "channel": "books5"},
            "action": "update",
            "data": [{"ts": "1235", "seqId": 45, "prevSeqId": 44,
                      "bids": [["100.1", "1", "0", "1"]],
                      "asks": [["100.3", "2", "0", "1"]]}],
        }), 9000)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, "snapshot")
        self.assertEqual(events[0].sequence, 45)
        self.assertEqual(events[0].sequence_start, 45)

    def test_okx_books_empty_equal_sequence_heartbeat_is_preserved(self) -> None:
        events = self.collector("okx")._parse(json.dumps({
            "arg": {"instId": "BTC-USDT", "channel": "books"},
            "action": "update",
            "data": [{"ts": "1235", "seqId": 44, "prevSeqId": 44,
                      "bids": [], "asks": []}],
        }), 9000)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, "heartbeat")
        self.assertEqual(events[0].sequence, 44)
        self.assertEqual(events[0].bids, ())
        self.assertEqual(events[0].asks, ())

    def test_okx_matching_heartbeat_refreshes_live_book(self) -> None:
        views = []
        collector = PublicL2WebSocketCollector(
            L2WebSocketConfig("okx", "BTC/USDT", "wss://example"),
            lambda _: None, on_book=views.append)
        collector.process_message(json.dumps({
            "arg": {"channel": "books", "instId": "BTC-USDT"},
            "action": "snapshot",
            "data": [{"ts": "1234", "seqId": 41, "prevSeqId": -1,
                      "bids": [["100", "2", "0", "1"]],
                      "asks": [["101", "3", "0", "1"]]}],
        }))
        self.assertTrue(views[-1].eligible)
        collector.process_message(json.dumps({
            "arg": {"channel": "books", "instId": "BTC-USDT"},
            "action": "update",
            "data": [{"ts": "1235", "seqId": 41, "prevSeqId": 41,
                      "bids": [], "asks": []}],
        }))
        self.assertTrue(views[-1].eligible)
        self.assertEqual(views[-1].sequence, 41)
        self.assertEqual(views[-1].bids[0].quantity, 2)
        self.assertEqual(collector.health_snapshot()["synchronizer"]["sequence"], 41)

    def test_okx_empty_data_invalidates_previous_eligible_view(self) -> None:
        views = []
        collector = PublicL2WebSocketCollector(
            L2WebSocketConfig("okx", "BTC/USDT", "wss://example"),
            lambda _: None, on_book=views.append)
        collector.process_message(json.dumps({
            "arg": {"channel": "books", "instId": "BTC-USDT"},
            "action": "snapshot",
            "data": [{"ts": "1234", "seqId": 41, "prevSeqId": -1,
                      "bids": [["100", "2", "0", "1"]],
                      "asks": [["101", "3", "0", "1"]]}],
        }))
        self.assertTrue(views[-1].eligible)
        collector.process_message(json.dumps({
            "arg": {"channel": "books", "instId": "BTC-USDT"},
            "action": "update", "data": [],
        }))
        self.assertFalse(views[-1].eligible)
        self.assertEqual(views[-1].reason, "parse_error")
        self.assertEqual(views[-1].bids, ())
        self.assertEqual(collector.health_snapshot()["parse_errors"], 1)

    def test_okx_books_equal_sequence_with_depth_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "invalid_okx_heartbeat"):
            self.collector("okx")._parse(json.dumps({
                "arg": {"instId": "BTC-USDT", "channel": "books"},
                "action": "update",
                "data": [{"ts": "1235", "seqId": 44, "prevSeqId": 44,
                          "bids": [["100.0", "2", "0", "3"]], "asks": []}],
            }), 9000)

    def test_okx_rejects_boolean_sequence(self) -> None:
        with self.assertRaisesRegex(ValueError, "invalid_okx_sequence"):
            self.collector("okx")._parse(json.dumps({
                "arg": {"instId": "BTC-USDT", "channel": "books"},
                "action": "update",
                "data": [{"ts": "1235", "seqId": True, "prevSeqId": 44,
                          "bids": [], "asks": []}],
            }), 9000)

    def test_okx_rejects_unknown_action(self) -> None:
        with self.assertRaisesRegex(ValueError, "invalid_okx_action"):
            self.collector("okx")._parse(json.dumps({
                "arg": {"instId": "BTC-USDT", "channel": "books"},
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


    def test_coinbase_collector_emits_synchronized_views_and_disconnect_invalidates(self) -> None:
        views = []
        collector = PublicL2WebSocketCollector(
            L2WebSocketConfig("coinbase", "BTC/USD", "wss://example"),
            lambda _: None,
            on_book=views.append,
        )
        collector.process_message(json.dumps({
            "channel": "l2_data", "sequence_num": 41,
            "events": [{"type": "snapshot", "product_id": "BTC-USD", "updates": [
                {"side": "bid", "price_level": "100", "new_quantity": "2"},
                {"side": "offer", "price_level": "101", "new_quantity": "3"},
            ]}],
        }))
        self.assertTrue(views[-1].eligible)
        self.assertEqual(views[-1].sequence, 41)
        collector._coinbase_sync.connection_lost()
        self.assertFalse(views[-1].eligible)
        self.assertEqual(views[-1].reason, "connection_lost")
        self.assertEqual(views[-1].bids, ())


    def test_okx_books_parser_preserves_empty_equal_sequence_heartbeat(self) -> None:
        collector = self.collector("okx")
        events = collector._parse(json.dumps({
            "arg": {"channel": "books", "instId": "BTC-USDT"},
            "action": "update",
            "data": [{"ts": "1235", "seqId": 44, "prevSeqId": 44, "bids": [], "asks": []}],
        }), 9000)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, "heartbeat")
        self.assertEqual(events[0].sequence, 44)
        self.assertIsNone(events[0].sequence_start)
        self.assertEqual(events[0].bids, ())
        self.assertEqual(events[0].asks, ())

    def test_okx_book_collector_reconstructs_and_invalidates_on_gap(self) -> None:
        views = []
        collector = PublicL2WebSocketCollector(
            L2WebSocketConfig("okx", "BTC/USDT", "wss://example"),
            lambda _: None,
            on_book=views.append,
        )
        collector.process_message(json.dumps({
            "arg": {"channel": "books", "instId": "BTC-USDT"},
            "action": "snapshot",
            "data": [{"ts": "1234", "seqId": 41, "prevSeqId": -1,
                      "bids": [["100", "2", "0", "1"]], "asks": [["101", "3", "0", "1"]]}],
        }))
        self.assertTrue(views[-1].eligible)
        self.assertEqual(views[-1].sequence, 41)
        collector.process_message(json.dumps({
            "arg": {"channel": "books", "instId": "BTC-USDT"},
            "action": "update",
            "data": [{"ts": "1235", "seqId": 42, "prevSeqId": 41,
                      "bids": [["100", "4", "0", "1"]], "asks": []}],
        }))
        self.assertTrue(views[-1].eligible)
        self.assertEqual(views[-1].bids[0].quantity, 4)
        collector.process_message(json.dumps({
            "arg": {"channel": "books", "instId": "BTC-USDT"},
            "action": "update",
            "data": [{"ts": "1236", "seqId": 44, "prevSeqId": 43,
                      "bids": [["100", "5", "0", "1"]], "asks": []}],
        }))
        self.assertFalse(views[-1].eligible)
        self.assertEqual(views[-1].reason, "sequence_gap")
        self.assertEqual(views[-1].bids, ())

    def test_okx_instrument_mismatch_invalidates_previous_view(self) -> None:
        views = []
        collector = PublicL2WebSocketCollector(
            L2WebSocketConfig("okx", "BTC/USDT", "wss://example"),
            lambda _: None,
            on_book=views.append,
        )
        collector.process_message(json.dumps({
            "arg": {"channel": "books", "instId": "BTC-USDT"},
            "action": "snapshot",
            "data": [{"ts": "1234", "seqId": 41, "prevSeqId": -1,
                      "bids": [["100", "2", "0", "1"]], "asks": [["101", "3", "0", "1"]]}],
        }))
        self.assertTrue(views[-1].eligible)
        collector.process_message(json.dumps({
            "arg": {"channel": "books", "instId": "ETH-USDT"},
            "action": "update",
            "data": [{"ts": "1235", "seqId": 42, "prevSeqId": 41, "bids": [], "asks": []}],
        }))
        self.assertFalse(views[-1].eligible)
        self.assertEqual(views[-1].reason, "parse_error")
        self.assertEqual(views[-1].bids, ())
