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

    def test_okx_trade_normalizes(self) -> None:
        collector = PublicWebSocketCollector(
            WebSocketMarketConfig("okx", "BTC/USDT", "wss://example"), lambda _: None)
        events = collector._parse(
            json.dumps({"arg": {"channel": "trades"},
                        "data": [{"ts": "1234", "tradeId": "88", "px": "100.1", "sz": "0.5"}]}), 8000)
        self.assertEqual(events[0].event_type, "trade")
        self.assertEqual(events[0].sequence, 88)
        self.assertEqual(events[0].price, 100.1)


if __name__ == "__main__":
    unittest.main()
