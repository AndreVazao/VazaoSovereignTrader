from __future__ import annotations

import unittest

from PC_ENGINE.market_events.binance_book_state import BookStatus
from PC_ENGINE.market_events.binance_book_sync import BinanceSpotBookSynchronizer
from PC_ENGINE.market_events.orderbook import OrderBookEvent, OrderBookLevel


class BinanceSpotBookSynchronizerTests(unittest.TestCase):
    def setUp(self):
        self.emitted = []
        self.sync = BinanceSpotBookSynchronizer(
            "BTC/USDT",
            self.emitted.append,
            snapshot_fetcher=lambda _symbol: (100, (OrderBookLevel(100.0, 2.0),), (OrderBookLevel(101.0, 3.0),)),
            max_buffer_events=3,
            max_age_ms=1000,
            max_levels=10,
        )

    def event(self, start, end, *, bids=(), asks=(), receive_ns=1_000_000):
        return OrderBookEvent(
            event_id=f"{start}-{end}",
            venue="binance",
            symbol="BTC/USDT",
            event_type="delta",
            sequence=end,
            sequence_start=start,
            provider_ts_ms=1000,
            exchange_ts_ms=1000,
            local_receive_ns=receive_ns,
            local_receive_wall_ns=1_000_000,
            bids=tuple(OrderBookLevel(*x) for x in bids),
            asks=tuple(OrderBookLevel(*x) for x in asks),
            raw_source="test",
        )

    def tearDown(self):
        self.sync.stop()

    def test_buffers_then_replays_contiguous_delta_after_snapshot(self):
        self.sync.on_event(self.event(99, 101, bids=((100.0, 4.0),)))
        self.assertEqual(self.sync.health()["buffered_events"], 1)
        self.assertTrue(self.sync.install_snapshot((
            100, (OrderBookLevel(100.0, 2.0),), (OrderBookLevel(101.0, 3.0),)
        )))
        view = self.sync.book.snapshot(2_000_000)
        self.assertEqual(view.status, BookStatus.SYNCED)
        self.assertTrue(view.eligible)
        self.assertEqual(view.update_id, 101)
        self.assertEqual(view.bids[0].quantity, 4.0)

    def test_old_buffered_events_do_not_mark_book_synced(self):
        self.sync.on_event(self.event(90, 99))
        self.assertTrue(self.sync.install_snapshot((
            100, (OrderBookLevel(100.0, 2.0),), (OrderBookLevel(101.0, 3.0),)
        )))
        self.assertEqual(self.sync.book.status, BookStatus.UNINITIALIZED)
        self.assertFalse(self.sync.book.snapshot(2_000_000).eligible)
        self.sync.on_event(self.event(101, 102, receive_ns=2_000_000))
        self.assertEqual(self.sync.book.status, BookStatus.SYNCED)

    def test_gap_invalidates_and_schedules_resnapshot(self):
        self.sync.install_snapshot((100, (OrderBookLevel(100.0, 2.0),), (OrderBookLevel(101.0, 3.0),)))
        self.sync.on_event(self.event(101, 101))
        self.sync.on_event(self.event(103, 103))
        self.assertEqual(self.sync.book.status, BookStatus.INVALID)
        self.assertEqual(self.sync.book.reason, "sequence_gap")
        self.assertTrue(self.sync.health()["sequence_gaps"] >= 1)

    def test_buffer_overflow_invalidates_without_emitting_a_book(self):
        for i in range(4):
            self.sync.on_event(self.event(101 + i, 101 + i))
        self.assertEqual(self.sync.book.status, BookStatus.INVALID)
        self.assertEqual(self.sync.book.reason, "buffer_overflow")
        self.assertEqual(self.sync.health()["buffer_overflows"], 1)
        self.assertEqual(len(self.emitted), 1)
        self.assertFalse(self.emitted[-1].eligible)
        self.assertEqual(self.emitted[-1].reason, "buffer_overflow")

    def test_gap_emits_invalidation_after_previously_eligible_view(self):
        self.sync.install_snapshot((100, (OrderBookLevel(100.0, 2.0),), (OrderBookLevel(101.0, 3.0),)))
        self.sync.on_event(self.event(101, 101, receive_ns=2_000_000))
        self.assertTrue(self.emitted[-1].eligible)
        self.sync.on_event(self.event(103, 103, receive_ns=3_000_000))
        self.assertFalse(self.emitted[-1].eligible)
        self.assertEqual(self.emitted[-1].status, BookStatus.INVALID)
        self.assertEqual(self.emitted[-1].reason, "sequence_gap")
        self.assertEqual(self.emitted[-1].bids, ())
        self.assertEqual(self.emitted[-1].asks, ())

    def test_health_reports_current_staleness_not_historical_eligibility(self):
        self.sync.install_snapshot((100, (OrderBookLevel(100.0, 2.0),), (OrderBookLevel(101.0, 3.0),)))
        self.sync.on_event(self.event(101, 101, receive_ns=1_000_000))
        health = self.sync.health()
        self.assertEqual(health["state"], BookStatus.SYNCED.value)
        self.assertFalse(health["eligible"])
        self.assertEqual(health["view_reason"], "stale")
        self.assertGreater(health["age_ms"], 1000)

    def test_connection_loss_invalidates_and_requires_resnapshot(self):
        self.sync.install_snapshot((100, (OrderBookLevel(100.0, 2.0),), (OrderBookLevel(101.0, 3.0),)))
        self.sync.on_event(self.event(101, 101))
        self.assertEqual(self.sync.book.status, BookStatus.SYNCED)
        self.sync.connection_lost()
        self.assertEqual(self.sync.book.status, BookStatus.INVALID)
        self.assertEqual(self.sync.book.reason, "connection_lost")
        self.assertFalse(self.sync.book.snapshot(2_000_000).eligible)
        self.assertFalse(self.emitted[-1].eligible)
        self.assertEqual(self.emitted[-1].reason, "connection_lost")

    def test_invalid_snapshot_does_not_enable_book(self):
        self.assertFalse(self.sync.install_snapshot((
            -1, (OrderBookLevel(100.0, 2.0),), (OrderBookLevel(101.0, 3.0),)
        )))
        self.assertFalse(self.sync.book.snapshot(2_000_000).eligible)

    def test_non_binance_or_wrong_symbol_events_are_ignored(self):
        wrong = self.event(101, 101)
        wrong = OrderBookEvent(**{**wrong.__dict__, "venue": "okx"})
        self.sync.on_event(wrong)
        self.assertEqual(self.sync.health()["buffered_events"], 0)


if __name__ == "__main__":
    unittest.main()
