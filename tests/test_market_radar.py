from __future__ import annotations

import tempfile
import unittest
from unittest.mock import patch

from PC_ENGINE.radar.market_radar import LeadLagObservation, MarketRadar, VenueSnapshot


class MarketRadarTests(unittest.TestCase):
    def test_detects_candidate_lead_lag_but_marks_polling_order_unconfirmed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            radar = MarketRadar.__new__(MarketRadar)
            radar.previous = {
                ("binance", "BTC/USDT"): VenueSnapshot("binance", "BTC/USDT", 100.0, 99.9, 100.1, 1000, 1000, 1100, None),
                ("okx", "BTC/USDT"): VenueSnapshot("okx", "BTC/USDT", 100.0, 99.9, 100.1, 1000, 1000, 1100, None),
            }
            current = [
                VenueSnapshot("okx", "BTC/USDT", 100.08, 100.0, 100.1, 1100, 2000, 2000, None),
                VenueSnapshot("binance", "BTC/USDT", 100.07, 100.0, 100.1, 1100, 2001, 2001, None),
            ]
            events = radar._detect_leads(current)
            self.assertEqual(len(events), 1)
            self.assertIsInstance(events[0], LeadLagObservation)
            self.assertEqual(events[0].leader, "okx")
            self.assertEqual(events[0].follower, "binance")
            self.assertEqual(events[0].direction, "UP")
            self.assertEqual(events[0].lag_ms, 1)
            self.assertEqual(events[0].evidence_status, "polling_order_unconfirmed")

    def test_pressure_is_normalized(self) -> None:
        radar = MarketRadar.__new__(MarketRadar)
        radar.previous = {
            ("binance", "BTC/USDT"): VenueSnapshot("binance", "BTC/USDT", 100.0, 0, 0, 0, None, 0, None),
        }
        snapshots = [VenueSnapshot("binance", "BTC/USDT", 100.1, 0, 0, 0, None, 1, None)]
        pressure = radar._pressure_from_previous(snapshots)
        self.assertGreater(pressure["BTC/USDT"], 0)
        self.assertLessEqual(pressure["BTC/USDT"], 1)

    def test_exchange_clock_difference_is_never_reported_as_latency(self) -> None:
        class Client:
            def fetch_ticker(self, _symbol):
                return {
                    "last": 100.0, "bid": 99.9, "ask": 100.1,
                    "baseVolume": 12.0, "timestamp": 1_700_000_000_000,
                }

        radar = MarketRadar.__new__(MarketRadar)
        radar.clients = {"binance": Client()}
        radar.symbols = ["BTC/USDT"]
        radar.previous = {}
        radar.last_pressure = {}
        radar.quality_rejections = 0
        radar._persist = lambda _snapshots, _leads: None
        with patch("PC_ENGINE.radar.market_radar.time.monotonic_ns", side_effect=[10_000_000, 13_500_000]), \
             patch("PC_ENGINE.radar.market_radar.time.time_ns", return_value=1_800_000_000_000_000_000):
            snapshots, leads = radar.snapshot()

        self.assertEqual(len(snapshots), 1)
        self.assertEqual(leads, [])
        self.assertIsNone(snapshots[0].latency_ms)
        self.assertEqual(snapshots[0].request_duration_ms, 3.5)
        self.assertEqual(
            snapshots[0].timing_quality,
            "source_timestamp_present_polling_order_unconfirmed",
        )
        self.assertEqual(snapshots[0].observation_status, "usable_for_descriptive_analysis_only")

    def test_duplicate_or_out_of_order_exchange_timestamp_is_rejected(self) -> None:
        class Client:
            def fetch_ticker(self, _symbol):
                return {
                    "last": 100.0, "bid": 99.9, "ask": 100.1,
                    "baseVolume": 12.0, "timestamp": 1_700_000_000_000,
                }

        radar = MarketRadar.__new__(MarketRadar)
        radar.clients = {"binance": Client()}
        radar.symbols = ["BTC/USDT"]
        radar.previous = {
            ("binance", "BTC/USDT"): VenueSnapshot(
                "binance", "BTC/USDT", 99.0, 98.9, 99.1, 12.0,
                1_700_000_000_000, 1_800_000_000_000, None,
            )
        }
        radar.last_pressure = {}
        radar.quality_rejections = 0
        radar._persist = lambda _snapshots, _leads: None
        with patch("PC_ENGINE.radar.market_radar.time.monotonic_ns", side_effect=[10, 20]), \
             patch("PC_ENGINE.radar.market_radar.time.time_ns", return_value=1_800_000_000_100_000_000):
            snapshots, leads = radar.snapshot()

        self.assertEqual(snapshots, [])
        self.assertEqual(leads, [])
        self.assertEqual(radar.quality_rejections, 1)
        self.assertEqual(radar.previous[("binance", "BTC/USDT")].price, 99.0)

    def test_malformed_exchange_timestamp_is_rejected_without_crashing(self) -> None:
        self.assertFalse(
            MarketRadar._validate_ticker_snapshot(
                price=100, bid=99.9, ask=100.1, volume=1, exchange_ts_ms=float("inf")
            )
        )
        self.assertFalse(
            MarketRadar._validate_ticker_snapshot(
                price=100, bid=99.9, ask=100.1, volume=1, exchange_ts_ms=float("nan")
            )
        )


    def test_ccxt_clients_receive_clamped_request_timeout(self) -> None:
        class Client:
            def __init__(self, options):
                self.options = options

            def load_markets(self):
                return {}

        captured = {}

        def factory(options):
            captured.update(options)
            return Client(options)

        with tempfile.TemporaryDirectory() as tmp, patch("PC_ENGINE.radar.market_radar.ccxt.binance", factory):
            MarketRadar(
                exchanges=["binance"],
                symbols=[],
                data_dir=tmp,
                request_timeout_ms=999999,
            )

        self.assertEqual(captured["timeout"], 60000)
        self.assertTrue(captured["enableRateLimit"])
    def test_snapshot_uses_shared_client_lock(self) -> None:
        class RecordingLock:
            def __init__(self):
                self.entered = False

            def __enter__(self):
                self.entered = True
                return self

            def __exit__(self, *_args):
                return False

        class Client:
            def fetch_ticker(self, _symbol):
                return {
                    "last": 100.0, "bid": 99.9, "ask": 100.1,
                    "baseVolume": 12.0, "timestamp": 1_700_000_000_000,
                }

        radar = MarketRadar.__new__(MarketRadar)
        lock = RecordingLock()
        radar.clients = {"binance": Client()}
        radar.client_locks = {"binance": lock}
        radar.symbols = ["BTC/USDT"]
        radar.previous = {}
        radar.last_pressure = {}
        radar.quality_rejections = 0
        radar.request_attempts = 0
        radar.successful_observations = 0
        radar.request_errors = 0
        radar.persistence_batches = 0
        radar.persistence_errors = 0
        radar.last_observation_ms = None
        radar.per_venue_metrics = {}
        radar._persist = lambda _snapshots, _leads: None

        radar.snapshot()

        self.assertTrue(lock.entered)

    def test_snapshot_stops_before_starting_another_request(self) -> None:
        import threading

        class Client:
            def __init__(self):
                self.calls = 0

            def fetch_ticker(self, _symbol):
                self.calls += 1
                raise AssertionError("cancelled radar must not start a request")

        event = threading.Event()
        event.set()
        client = Client()
        radar = MarketRadar.__new__(MarketRadar)
        radar.clients = {"binance": client}
        radar.symbols = ["BTC/USDT"]
        radar.previous = {}
        radar.last_pressure = {}
        radar.quality_rejections = 0
        radar.stop_event = event
        radar._persist = lambda _snapshots, _leads: None

        snapshots, leads = radar.snapshot()

        self.assertEqual(snapshots, [])
        self.assertEqual(leads, [])
        self.assertEqual(client.calls, 0)


    def test_collection_metrics_separate_success_quality_rejection_and_request_error(self):
        class Client:
            def __init__(self):
                self.results = iter([
                    {"last": 100.0, "bid": 99.9, "ask": 100.1, "baseVolume": 12.0, "timestamp": 1700000000000},
                    {"last": 0.0, "bid": 0.0, "ask": 0.0, "baseVolume": 0.0, "timestamp": 1700000001000},
                    RuntimeError("venue unavailable"),
                ])

            def fetch_ticker(self, _symbol):
                result = next(self.results)
                if isinstance(result, Exception):
                    raise result
                return result

        radar = MarketRadar.__new__(MarketRadar)
        radar.clients = {"binance": Client()}
        radar.exchanges = ["binance"]
        radar.symbols = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]
        radar.previous = {}
        radar.last_pressure = {}
        radar.quality_rejections = 0
        radar.request_attempts = 0
        radar.successful_observations = 0
        radar.request_errors = 0
        radar.persistence_batches = 0
        radar.persistence_errors = 0
        radar.last_observation_ms = None
        radar.per_venue_metrics = {
            "binance": {"attempts": 0, "successes": 0, "errors": 0, "quality_rejections": 0}
        }
        persisted = []
        radar._persist = lambda snapshots, leads: persisted.append((snapshots, leads))

        snapshots, _ = radar.snapshot()
        metrics = radar.collection_metrics()

        self.assertEqual(len(snapshots), 1)
        self.assertEqual(metrics["request_attempts"], 3)
        self.assertEqual(metrics["successful_observations"], 1)
        self.assertEqual(metrics["request_errors"], 1)
        self.assertEqual(metrics["quality_rejections"], 1)
        self.assertEqual(metrics["persistence_batches"], 1)
        self.assertEqual(metrics["persistence_errors"], 0)
        self.assertEqual(metrics["venues"]["binance"]["successes"], 1)
        self.assertFalse(metrics["private_account_access"])
        self.assertFalse(metrics["order_authority"])
        self.assertEqual(len(persisted), 1)

    def test_collection_metrics_count_persistence_failure(self):
        radar = MarketRadar.__new__(MarketRadar)
        radar.clients = {}
        radar.exchanges = []
        radar.symbols = []
        radar.previous = {}
        radar.last_pressure = {}
        radar.quality_rejections = 0
        radar.request_attempts = 0
        radar.successful_observations = 0
        radar.request_errors = 0
        radar.persistence_batches = 0
        radar.persistence_errors = 0
        radar.last_observation_ms = None
        radar.per_venue_metrics = {}

        def fail_persist(_snapshots, _leads):
            raise OSError("disk unavailable")

        radar._persist = fail_persist
        with self.assertRaises(OSError):
            radar.snapshot()
        self.assertEqual(radar.collection_metrics()["persistence_errors"], 1)


if __name__ == "__main__":
    unittest.main()
