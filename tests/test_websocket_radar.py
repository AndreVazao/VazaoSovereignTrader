from __future__ import annotations

import tempfile
import unittest

from PC_ENGINE.radar.websocket_radar import MarketEvent, WebSocketMarketRadar


class WebSocketRadarTests(unittest.TestCase):
    def test_binance_trade_is_normalized(self) -> None:
        radar = WebSocketMarketRadar.__new__(WebSocketMarketRadar)
        radar.symbols = ["BTC/USDT"]
        radar._last_price = {}
        payload = {
            "stream": "btcusdt@trade",
            "data": {"e": "trade", "s": "BTCUSDT", "p": "100.0", "q": "0.25", "T": 1234567890, "m": False},
        }
        events = radar._parse_binance(payload, 1234567990)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].symbol, "BTC/USDT")
        self.assertEqual(events[0].side, "BUY")
        self.assertEqual(events[0].exchange_ts_ms, 1234567890)
        self.assertIsNone(events[0].price_before)

    def test_make_event_does_not_mislabel_clock_difference_as_latency(self) -> None:
        radar = WebSocketMarketRadar.__new__(WebSocketMarketRadar)
        radar._last_price = {}
        event = radar._make_event("binance", "BTC/USDT", 100.0, 1.0, "BUY", 1_000, 9_000)
        self.assertEqual(event.exchange_ts_ms, 1_000)
        self.assertEqual(event.local_ts_ms, 9_000)
        self.assertIsNone(event.local_receive_latency_ms)

    def test_reconnect_backoff_grows_after_short_disconnects(self) -> None:
        next_delay = WebSocketMarketRadar._next_reconnect_delay
        self.assertEqual(next_delay(1.0, 0.2), 2.0)
        self.assertEqual(next_delay(2.0, 0.2), 4.0)
        self.assertEqual(next_delay(20.0, 0.2), 30.0)

    def test_reconnect_backoff_resets_only_after_stable_connection(self) -> None:
        next_delay = WebSocketMarketRadar._next_reconnect_delay
        self.assertEqual(next_delay(30.0, 59.9), 30.0)
        self.assertEqual(next_delay(30.0, 60.0), 1.0)

    def test_candidate_requires_move_threshold(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            radar = WebSocketMarketRadar(["BTC/USDT"], exchanges=[], data_dir=tmp, min_move_bps=5, lead_window_ms=750)
            radar._last_price[("binance", "BTC/USDT")] = 100.0
            small = MarketEvent("binance", "BTC/USDT", 100.01, 1, "BUY", 1000, 1001, 1, 100.0)
            radar._emit(small)
            self.assertEqual(radar._last_move, {})

    def test_lead_lag_candidate_is_persisted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            radar = WebSocketMarketRadar(["BTC/USDT"], exchanges=[], data_dir=tmp, min_move_bps=5, lead_window_ms=750)
            leader = MarketEvent("okx", "BTC/USDT", 100.10, 1, "BUY", 1000, 1001, 1, 100.0)
            follower = MarketEvent("binance", "BTC/USDT", 100.10, 1, "BUY", 1050, 1051, 1, 100.0)
            radar._emit(leader)
            radar._emit(follower)
            text = (radar.data_dir / "websocket_lead_lag.jsonl").read_text(encoding="utf-8")
            self.assertIn('"leader": "okx"', text)
            self.assertIn('"follower": "binance"', text)
            self.assertIn('"exchange_lag_ms": 50', text)


if __name__ == "__main__":
    unittest.main()
