from __future__ import annotations

import json
import unittest

from PC_ENGINE.market_events.websocket_collectors import PublicWebSocketCollector, WebSocketMarketConfig


class WebSocketCollectorTests(unittest.TestCase):
    def test_binance_book_ticker_normalizes(self) -> None:
        collector = PublicWebSocketCollector(
            WebSocketMarketConfig("binance", "BTC/USDT", "wss://example"), lambda _: None)
        events = collector._parse(
            json.dumps({"e": "bookTicker", "E": 1234, "u": 77, "b": "100.0", "a": "100.2"}), 9000)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, "ticker")
        self.assertEqual(events[0].sequence, 77)
        self.assertEqual(events[0].local_receive_ns, 9000)

    def test_binance_book_ticker_without_event_type_normalizes(self) -> None:
        collector = PublicWebSocketCollector(
            WebSocketMarketConfig("binance", "BTC/USDT", "wss://example"), lambda _: None)
        events = collector._parse(
            json.dumps({"u": 77, "s": "BTCUSDT", "b": "100.0", "B": "1.0", "a": "100.2", "A": "2.0"}),
            9000)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, "ticker")
        self.assertEqual(events[0].bid, 100.0)
        self.assertEqual(events[0].ask, 100.2)
        self.assertEqual(events[0].sequence, 77)

    def test_okx_trade_normalizes(self) -> None:
        collector = PublicWebSocketCollector(
            WebSocketMarketConfig("okx", "BTC/USDT", "wss://example"), lambda _: None)
        events = collector._parse(
            json.dumps({"arg": {"channel": "trades"},
                        "data": [{"ts": "1234", "tradeId": "88", "px": "100.1", "sz": "0.5"}]}), 8000)
        self.assertEqual(events[0].event_type, "trade")
        self.assertEqual(events[0].sequence, 88)
        self.assertEqual(events[0].price, 100.1)

    def test_okx_ticker_preserves_bid_ask_for_spread_research(self) -> None:
        collector = PublicWebSocketCollector(
            WebSocketMarketConfig("okx", "BTC/USDT", "wss://example"), lambda _: None)
        events = collector._parse(
            json.dumps({"arg": {"channel": "tickers"},
                        "data": [{"ts": "1234", "bidPx": "100.0", "askPx": "100.2", "last": "100.1"}]}),
            9000)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, "ticker")
        self.assertEqual(events[0].bid, 100.0)
        self.assertEqual(events[0].ask, 100.2)
        self.assertEqual(events[0].exchange_ts_ms, 1234)
        self.assertGreater(events[0].local_receive_wall_ns, 0)

    def test_coinbase_ticker_preserves_bid_ask_for_spread_research(self) -> None:
        collector = PublicWebSocketCollector(
            WebSocketMarketConfig("coinbase", "BTC/USDT", "wss://example"), lambda _: None)
        events = collector._parse(
            json.dumps({"events": [{"tickers": [
                {"best_bid": "100.0", "best_ask": "100.2", "price": "100.1"}
            ]}]}),
            9000)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, "ticker")
        self.assertEqual(events[0].bid, 100.0)
        self.assertEqual(events[0].ask, 100.2)
        self.assertIsNone(events[0].exchange_ts_ms)
        self.assertGreater(events[0].local_receive_wall_ns, 0)

    def test_snapshot_exposes_paper_safe_operational_state(self) -> None:
        received = []
        collector = PublicWebSocketCollector(
            WebSocketMarketConfig("coinbase", "BTC/USDT", "wss://example"),
            received.append,
        )
        initial = collector.snapshot()
        self.assertEqual(initial["state"], "IDLE")
        self.assertEqual(initial["connect_attempts"], 0)
        self.assertEqual(initial["events_emitted"], 0)
        self.assertTrue(initial["paper_only"])
        self.assertFalse(initial["orders_submitted"])
        self.assertFalse(initial["execution_authorized"])

        event = collector._parse(
            json.dumps({"events": [{"tickers": [
                {"best_bid": "100.0", "best_ask": "100.2", "price": "100.1"}
            ]}]}),
            9000,
        )[0]
        collector._emit(event)
        snapshot = collector.snapshot()
        self.assertEqual(snapshot["events_emitted"], 1)
        self.assertEqual(len(received), 1)
        self.assertIsNotNone(snapshot["last_event_age_ms"])
        self.assertIsNone(snapshot["last_error"])


if __name__ == "__main__":
    unittest.main()
