from __future__ import annotations

import json
import tempfile
import unittest
from unittest.mock import patch

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

    def test_trade_parsers_reject_missing_or_invalid_side(self) -> None:
        radar = WebSocketMarketRadar.__new__(WebSocketMarketRadar)
        radar.symbols = ["BTC/USDT", "BTC/USD"]
        radar._last_price = {}

        # Binance must provide its boolean maker flag; missing/malformed flags
        # must not silently turn an unknown aggressor side into BUY.
        self.assertEqual(radar._parse_binance({
            "data": {"e": "trade", "s": "BTCUSDT", "p": "100", "q": "1",
                     "T": 1234567890}
        }, 1234567990), [])
        self.assertEqual(radar._parse_binance({
            "data": {"e": "trade", "s": "BTCUSDT", "p": "100", "q": "1",
                     "T": 1234567890, "m": "false"}
        }, 1234567990), [])

        coinbase = radar._parse_coinbase({
            "channel": "market_trades",
            "events": [{"trades": [{
                "product_id": "BTC-USD", "price": "100", "size": "1",
                "side": "", "time": "2026-10-21T12:00:00Z",
            }]}],
        }, 1234567990)
        self.assertEqual(coinbase, [])

        okx = radar._parse_okx({
            "arg": {"channel": "trades"},
            "data": [{"instId": "BTC-USDT", "px": "100", "sz": "1",
                      "side": "unknown", "ts": "1234567890"}],
        }, 1234567990)
        self.assertEqual(okx, [])

    def test_venue_trade_ids_are_preserved_for_deduplication(self) -> None:
        radar = WebSocketMarketRadar.__new__(WebSocketMarketRadar)
        radar.symbols = ["BTC/USDT", "BTC/USD"]
        radar._last_price = {}

        binance = radar._parse_binance({
            "data": {"e": "trade", "s": "BTCUSDT", "p": "100", "q": "1",
                     "T": 1234567890, "m": False, "t": 77},
        }, 1234567990)
        self.assertEqual(binance[0].trade_id, "77")

        coinbase = radar._parse_coinbase({
            "channel": "market_trades",
            "events": [{"trades": [{
                "product_id": "BTC-USD", "price": "100", "size": "1",
                "side": "BUY", "time": "2026-10-21T12:00:00Z", "trade_id": "cb-77",
            }]}],
        }, 1234567990)
        self.assertEqual(coinbase[0].trade_id, "cb-77")

        okx = radar._parse_okx({
            "arg": {"channel": "trades"},
            "data": [{"instId": "BTC-USDT", "px": "100", "sz": "1",
                      "side": "buy", "ts": "1234567890", "tradeId": "okx-77"}],
        }, 1234567990)
        self.assertEqual(okx[0].trade_id, "okx-77")

    def test_replayed_trade_id_is_ignored_without_duplicate_event_or_callback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            callbacks = []
            radar = WebSocketMarketRadar(
                ["BTC/USDT"], exchanges=[], data_dir=tmp, callback=callbacks.append,
            )
            first = MarketEvent(
                "binance", "BTC/USDT", 100.0, 1.0, "BUY",
                1000, 1001, None, None, "trade-123",
            )
            replay = MarketEvent(
                "binance", "BTC/USDT", 100.0, 1.0, "BUY",
                1000, 1010, None, None, "trade-123",
            )

            radar._emit(first)
            radar._emit(replay)

            self.assertEqual(radar.snapshot()["events_total"], 1)
            self.assertEqual(len(callbacks), 1)
            rows = (radar.data_dir / "websocket_events.jsonl").read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(rows), 1)

    def test_binance_missing_trade_timestamp_is_rejected_not_replaced_with_receive_time(self) -> None:
        radar = WebSocketMarketRadar.__new__(WebSocketMarketRadar)
        radar.symbols = ["BTC/USDT"]
        radar._last_price = {}
        payload = {
            "data": {"e": "trade", "s": "BTCUSDT", "p": "100.0", "q": "0.25", "E": 1234567890, "m": False},
        }
        self.assertEqual(radar._parse_binance(payload, 1234567990), [])

    def test_coinbase_missing_or_malformed_trade_timestamp_is_rejected(self) -> None:
        radar = WebSocketMarketRadar.__new__(WebSocketMarketRadar)
        radar.symbols = ["BTC/USD"]
        radar._last_price = {}
        missing = {"channel": "market_trades", "events": [{"trades": [
            {"product_id": "BTC-USD", "price": "100", "size": "1", "side": "BUY"}
        ]}]}
        malformed = {"channel": "market_trades", "events": [{"trades": [
            {"product_id": "BTC-USD", "price": "100", "size": "1", "side": "BUY", "time": "not-a-time"}
        ]}]}
        self.assertEqual(radar._parse_coinbase(missing, 1234567990), [])
        self.assertEqual(radar._parse_coinbase(malformed, 1234567990), [])

    def test_okx_missing_trade_timestamp_is_rejected_not_replaced_with_receive_time(self) -> None:
        radar = WebSocketMarketRadar.__new__(WebSocketMarketRadar)
        radar.symbols = ["BTC/USDT"]
        radar._last_price = {}
        payload = {"arg": {"channel": "trades"}, "data": [
            {"instId": "BTC-USDT", "px": "100", "sz": "1", "side": "buy"}
        ]}
        self.assertEqual(radar._parse_okx(payload, 1234567990), [])

    def test_message_processing_errors_are_counted_without_raw_exception_text(self) -> None:
        radar = WebSocketMarketRadar.__new__(WebSocketMarketRadar)
        radar._lock = __import__("threading").RLock()
        radar._message_errors = {"binance": 0}
        radar._last_message_error = {}

        radar._record_message_error("binance", ValueError("sensitive raw payload detail"))
        snapshot = {"message_errors": dict(radar._message_errors),
                    "last_message_error": dict(radar._last_message_error)}

        self.assertEqual(snapshot["message_errors"]["binance"], 1)
        self.assertEqual(snapshot["last_message_error"]["binance"], "ValueError")
        self.assertNotIn("sensitive raw payload detail", str(snapshot))

    def test_message_callback_records_decode_and_parser_failures(self) -> None:
        import threading

        cases = [
            ("{malformed-json", None, "JSONDecodeError"),
            ('{"data":{}}', ValueError("sensitive parser detail"), "ValueError"),
        ]

        for raw, parser_error, expected_error in cases:
            with self.subTest(expected_error=expected_error), tempfile.TemporaryDirectory() as tmp:
                holder = {}

                class MessageWebSocketApp:
                    def __init__(self, url, on_open=None, on_message=None):
                        self.on_open = on_open
                        self.on_message = on_message

                    def run_forever(self, **kwargs):
                        if self.on_open:
                            self.on_open(self)
                        if self.on_message:
                            self.on_message(self, raw)
                        holder["radar"]._stop.set()

                    def close(self):
                        pass

                radar = WebSocketMarketRadar(
                    ["BTC/USDT"], exchanges=["binance"], data_dir=tmp,
                )
                holder["radar"] = radar
                parser_patch = patch.object(
                    radar, "_parse_binance",
                    side_effect=parser_error if parser_error is not None else None,
                )
                with parser_patch, patch(
                    "PC_ENGINE.radar.websocket_radar.websocket.WebSocketApp",
                    MessageWebSocketApp,
                ):
                    if parser_error is None:
                        # Keep the real parser for malformed JSON; json.loads fails first.
                        parser_patch.stop()
                    else:
                        parser_patch.start()
                    radar.start()
                    for worker in list(radar._threads):
                        worker.join(timeout=2)
                    snapshot = radar.snapshot()
                    radar.stop()

                self.assertEqual(snapshot["message_errors"]["binance"], 1)
                self.assertEqual(snapshot["last_message_error"]["binance"], expected_error)
                self.assertNotIn("sensitive parser detail", str(snapshot))

    def test_snapshot_reports_no_trade_yet_without_claiming_disconnect(self) -> None:
        radar = WebSocketMarketRadar.__new__(WebSocketMarketRadar)
        radar.symbols = ["BTC/USDT"]
        radar.exchanges = ["binance", "okx"]
        radar._threads = []
        radar._lock = __import__("threading").RLock()
        radar._last_event = {}
        radar._connection_state = {"binance": "never_connected", "okx": "never_connected"}
        radar._last_connected_ts_ms = {}
        radar._last_disconnected_ts_ms = {}
        radar._last_message_ts_ms = {}
        radar._last_connection_error = {}
        radar._events_total = 0
        radar._events_by_exchange = {}
        radar._reconnects = {"binance": 0, "okx": 0}
        radar._errors = {"binance": 0, "okx": 0}
        radar._message_errors = {"binance": 0, "okx": 0}
        radar._last_message_error = {}
        radar._persistence_errors = 0
        snapshot = radar.snapshot()
        self.assertEqual(snapshot["trade_freshness"]["binance"], "no_trade_yet")
        self.assertEqual(snapshot["connection_state"]["binance"], "never_connected")
        self.assertEqual(snapshot["last_message_ts_ms"], {})
        self.assertFalse(snapshot["worker_alive"]["binance"])

    def test_snapshot_marks_old_trade_as_no_recent_trade(self) -> None:
        radar = WebSocketMarketRadar.__new__(WebSocketMarketRadar)
        radar.symbols = ["BTC/USDT"]
        radar.exchanges = ["binance"]
        radar._threads = []
        radar._lock = __import__("threading").RLock()
        radar._last_event = {"binance": {"local_ts_ms": 1, "symbol": "BTC/USDT", "price": 100.0}}
        radar._connection_state = {"binance": "never_connected"}
        radar._last_connected_ts_ms = {}
        radar._last_disconnected_ts_ms = {}
        radar._last_message_ts_ms = {}
        radar._last_connection_error = {}
        radar._events_total = 1
        radar._events_by_exchange = {"binance": 1}
        radar._reconnects = {"binance": 0}
        radar._errors = {"binance": 0}
        radar._message_errors = {"binance": 0}
        radar._last_message_error = {}
        radar._persistence_errors = 0
        snapshot = radar.snapshot()
        self.assertEqual(snapshot["trade_freshness"]["binance"], "no_recent_trade")
        self.assertGreater(snapshot["last_event_age_ms"]["binance"], 30_000)

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

    def test_start_is_idempotent_while_worker_is_alive(self) -> None:
        import threading

        with tempfile.TemporaryDirectory() as tmp:
            radar = WebSocketMarketRadar(["BTC/USDT"], exchanges=["binance"], data_dir=tmp)
            release = threading.Event()
            entered = threading.Event()

            def worker() -> None:
                entered.set()
                release.wait(timeout=2)

            with patch.object(radar, "_run_binance", side_effect=worker):
                radar.start()
                self.assertTrue(entered.wait(timeout=1))
                radar.start()
                self.assertEqual(len(radar._threads), 1)
                self.assertTrue(radar.snapshot()["running"])
                release.set()
                radar.stop()
                self.assertFalse(radar.snapshot()["running"])

    def test_stop_closes_active_websocket_and_reports_worker_stopped(self) -> None:
        import threading

        created = threading.Event()
        opened = threading.Event()
        closed = threading.Event()

        class FakeWebSocketApp:
            def __init__(self, url, on_open=None, on_message=None):
                self.url = url
                self.on_open = on_open
                self.on_message = on_message
                created.set()

            def run_forever(self, **kwargs):
                if self.on_open:
                    self.on_open(self)
                if self.on_message:
                    self.on_message(self, json.dumps({
                        "data": {"e": "trade", "s": "BTCUSDT", "p": "100",
                                 "q": "1", "T": 1761048000000, "m": False, "t": 1}
                    }))
                opened.set()
                closed.wait(timeout=5)

            def close(self):
                closed.set()

        with tempfile.TemporaryDirectory() as tmp:
            radar = WebSocketMarketRadar(["BTC/USDT"], exchanges=["binance"], data_dir=tmp)
            with patch("PC_ENGINE.radar.websocket_radar.websocket.WebSocketApp", FakeWebSocketApp):
                radar.start()
                self.assertTrue(created.wait(timeout=1))
                self.assertTrue(opened.wait(timeout=1))
                connected = radar.snapshot()
                self.assertEqual(connected["connection_state"]["binance"], "connected")
                self.assertIn("binance", connected["last_message_ts_ms"])
                self.assertIn("binance", connected["last_connected_ts_ms"])
                radar.stop()
                stopped = radar.snapshot()
                self.assertFalse(stopped["running"])
                self.assertEqual(stopped["connection_state"]["binance"], "stopped")
                self.assertIn("binance", stopped["last_disconnected_ts_ms"])
                self.assertEqual(radar._threads, [])

    def test_failed_connect_is_not_reported_as_disconnected(self) -> None:
        import threading

        attempted = threading.Event()
        holder = {}

        class FailingConnectWebSocketApp:
            def __init__(self, url, on_open=None, on_message=None):
                pass

            def run_forever(self, **kwargs):
                attempted.set()
                holder["radar"]._stop.set()
                raise RuntimeError("simulated connection failure")

            def close(self):
                pass

        with tempfile.TemporaryDirectory() as tmp:
            radar = WebSocketMarketRadar(["BTC/USDT"], exchanges=["binance"], data_dir=tmp)
            holder["radar"] = radar
            with patch("PC_ENGINE.radar.websocket_radar.websocket.WebSocketApp", FailingConnectWebSocketApp):
                radar.start()
                self.assertTrue(attempted.wait(timeout=1))
                radar._threads[0].join(timeout=1)
                snapshot = radar.snapshot()

            self.assertEqual(snapshot["connection_state"]["binance"], "stopped")
            self.assertEqual(snapshot["last_connection_error"]["binance"], "RuntimeError")
            self.assertNotIn("binance", snapshot["last_disconnected_ts_ms"])

    def test_start_during_shutdown_does_not_restart_workers(self) -> None:
        import threading

        created = threading.Event()
        closing = threading.Event()
        allow_close = threading.Event()
        closed = threading.Event()

        class BlockingCloseWebSocketApp:
            def __init__(self, url, on_open=None, on_message=None):
                self.url = url
                created.set()

            def run_forever(self, **kwargs):
                closed.wait(timeout=5)

            def close(self):
                closing.set()
                allow_close.wait(timeout=2)
                closed.set()

        with tempfile.TemporaryDirectory() as tmp:
            radar = WebSocketMarketRadar(["BTC/USDT"], exchanges=["binance"], data_dir=tmp)
            with patch("PC_ENGINE.radar.websocket_radar.websocket.WebSocketApp", BlockingCloseWebSocketApp):
                radar.start()
                self.assertTrue(created.wait(timeout=1))
                stopper = threading.Thread(target=radar.stop)
                stopper.start()
                self.assertTrue(closing.wait(timeout=1))

                # start() must not clear the stop event or spawn a second worker
                # while stop() is still closing/joining the original worker.
                radar.start()
                self.assertEqual(len(radar._threads), 1)

                allow_close.set()
                stopper.join(timeout=2)
                self.assertFalse(stopper.is_alive())
                self.assertFalse(radar.snapshot()["running"])
                self.assertEqual(radar._threads, [])

    def test_stop_retries_close_if_first_close_precedes_run_forever(self) -> None:
        import threading

        check_reached = threading.Event()
        allow_check = threading.Event()
        run_entered = threading.Event()
        first_close = threading.Event()
        closed = threading.Event()

        class PausingStopEvent:
            def __init__(self):
                self.event = threading.Event()
                self.calls = 0

            def is_set(self):
                self.calls += 1
                value = self.event.is_set()
                if self.calls == 2:
                    check_reached.set()
                    allow_check.wait(timeout=2)
                return value

            def set(self):
                self.event.set()

            def clear(self):
                self.event.clear()

            def wait(self, timeout=None):
                return self.event.wait(timeout)

        class StartupRaceWebSocketApp:
            def __init__(self, url, on_open=None, on_message=None):
                pass

            def run_forever(self, **kwargs):
                run_entered.set()
                # Model websocket-client resetting its internal run flag when
                # run_forever starts, after an earlier close was too early.
                closed.clear()
                closed.wait(timeout=5)

            def close(self):
                first_close.set()
                closed.set()

        with tempfile.TemporaryDirectory() as tmp:
            radar = WebSocketMarketRadar(["BTC/USDT"], exchanges=["binance"], data_dir=tmp)
            radar._stop = PausingStopEvent()
            with patch("PC_ENGINE.radar.websocket_radar.websocket.WebSocketApp", StartupRaceWebSocketApp):
                radar.start()
                self.assertTrue(check_reached.wait(timeout=1))
                stopper = threading.Thread(target=radar.stop)
                stopper.start()
                self.assertTrue(first_close.wait(timeout=1))

                # The worker already passed its stop check but has not entered
                # run_forever yet; allow it to enter after the first close.
                allow_check.set()
                self.assertTrue(run_entered.wait(timeout=1))
                stopper.join(timeout=2)
                self.assertFalse(stopper.is_alive())
                self.assertFalse(radar.snapshot()["running"])
                self.assertEqual(radar._threads, [])

    def test_candidate_requires_move_threshold(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            radar = WebSocketMarketRadar(["BTC/USDT"], exchanges=[], data_dir=tmp, min_move_bps=5, lead_window_ms=750)
            radar._last_price[("binance", "BTC/USDT")] = 100.0
            small = MarketEvent("binance", "BTC/USDT", 100.01, 1, "BUY", 1000, 1001, 1, 100.0)
            radar._emit(small)
            self.assertEqual(radar._last_move, {})

    def test_persistence_failure_is_reported_without_stopping_radar(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            radar = WebSocketMarketRadar(["BTC/USDT"], exchanges=[], data_dir=tmp)
            event = MarketEvent("binance", "BTC/USDT", 100.0, 1.0, "BUY", 1000, 1001, None)
            with patch("pathlib.Path.open", side_effect=OSError("disk unavailable")):
                radar._emit(event)
            snapshot = radar.snapshot()
            self.assertEqual(snapshot["events_total"], 1)
            self.assertEqual(snapshot["persistence_errors"], 1)
            self.assertEqual(snapshot["last_event"]["binance"]["price"], 100.0)

    def test_lead_lag_rejects_receive_order_inversion_and_stale_delivery(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            radar = WebSocketMarketRadar(
                ["BTC/USDT"], exchanges=[], data_dir=tmp,
                min_move_bps=5, lead_window_ms=750,
            )
            leader = MarketEvent("okx", "BTC/USDT", 100.10, 1, "BUY", 1000, 1100, None, 100.0)

            cases = (
                ("receive order inverted", 1050, 1051),
                ("received too late", 1050, 2000),
            )
            for label, follower_exchange_ts, follower_local_ts in cases:
                with self.subTest(case=label):
                    follower = MarketEvent(
                        "binance", "BTC/USDT", 100.10, 1, "BUY",
                        follower_exchange_ts, follower_local_ts, None, 100.0,
                    )
                    with patch.object(radar, "_persist_lead_lag") as persist:
                        radar._match_candidate(follower, [(("okx", "BTC/USDT"), leader)])
                        persist.assert_not_called()

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


    def test_public_trade_parsers_reject_non_finite_or_invalid_prices(self) -> None:
        radar = WebSocketMarketRadar.__new__(WebSocketMarketRadar)
        radar.symbols = ["BTC/USDT", "BTC/USD"]
        radar._last_price = {}

        binance_base = {"e": "trade", "s": "BTCUSDT", "q": "1", "T": 1234567890, "m": False}
        for invalid_price in ("nan", "inf", "-inf", "0", "-1", "not-a-number"):
            with self.subTest(exchange="binance", price=invalid_price):
                payload = {"data": {**binance_base, "p": invalid_price}}
                self.assertEqual(radar._parse_binance(payload, 1234567990), [])

        coinbase_base = {
            "channel": "market_trades",
            "events": [{"trades": [{
                "product_id": "BTC-USD", "size": "1", "side": "BUY",
                "time": "2026-10-21T12:00:00Z",
            }]}],
        }
        for invalid_price in ("nan", "inf", "0", "-1", "broken"):
            with self.subTest(exchange="coinbase", price=invalid_price):
                payload = {
                    **coinbase_base,
                    "events": [{"trades": [{**coinbase_base["events"][0]["trades"][0], "price": invalid_price}]}],
                }
                self.assertEqual(radar._parse_coinbase(payload, 1234567990), [])

        okx_base = {
            "arg": {"channel": "trades"},
            "data": [{"instId": "BTC-USDT", "sz": "1", "side": "buy", "ts": "1234567890"}],
        }
        for invalid_price in ("nan", "inf", "0", "-1", "broken"):
            with self.subTest(exchange="okx", price=invalid_price):
                payload = {
                    **okx_base,
                    "data": [{**okx_base["data"][0], "px": invalid_price}],
                }
                self.assertEqual(radar._parse_okx(payload, 1234567990), [])

    def test_public_trade_parsers_reject_negative_or_non_finite_quantities(self) -> None:
        radar = WebSocketMarketRadar.__new__(WebSocketMarketRadar)
        radar.symbols = ["BTC/USDT", "BTC/USD"]
        radar._last_price = {}

        binance_base = {"e": "trade", "s": "BTCUSDT", "p": "100", "T": 1234567890, "m": False}
        for invalid_quantity in ("nan", "inf", "-inf", "0", "-1", "broken"):
            with self.subTest(exchange="binance", quantity=invalid_quantity):
                self.assertEqual(
                    radar._parse_binance({"data": {**binance_base, "q": invalid_quantity}}, 1234567990),
                    [],
                )

        coinbase_trade = {
            "product_id": "BTC-USD", "price": "100", "side": "BUY",
            "time": "2026-10-21T12:00:00Z",
        }
        for invalid_quantity in ("nan", "inf", "0", "-1", "broken"):
            with self.subTest(exchange="coinbase", quantity=invalid_quantity):
                payload = {"channel": "market_trades", "events": [{"trades": [{**coinbase_trade, "size": invalid_quantity}]}]}
                self.assertEqual(radar._parse_coinbase(payload, 1234567990), [])

        okx_trade = {"instId": "BTC-USDT", "px": "100", "side": "buy", "ts": "1234567890"}
        for invalid_quantity in ("nan", "inf", "-1", "broken"):
            with self.subTest(exchange="okx", quantity=invalid_quantity):
                payload = {"arg": {"channel": "trades"}, "data": [{**okx_trade, "sz": invalid_quantity}]}
                self.assertEqual(radar._parse_okx(payload, 1234567990), [])

    def test_public_trade_parsers_reject_zero_quantity(self) -> None:
        radar = WebSocketMarketRadar.__new__(WebSocketMarketRadar)
        radar.symbols = ["BTC/USDT"]
        radar._last_price = {}
        payload = {"data": {"e": "trade", "s": "BTCUSDT", "p": "100", "q": "0", "T": 1234567890, "m": False}}
        self.assertEqual(radar._parse_binance(payload, 1234567990), [])



if __name__ == "__main__":
    unittest.main()
