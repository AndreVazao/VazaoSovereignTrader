from __future__ import annotations

import unittest

from PC_ENGINE.market_events.coinbase_book_sync import CoinbaseL2BookSynchronizer
from PC_ENGINE.market_events.orderbook import OrderBookEvent, OrderBookLevel


class CoinbaseL2BookSynchronizerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.views = []
        self.sync = CoinbaseL2BookSynchronizer("BTC/USD", self.views.append, max_age_ms=1000)

    @staticmethod
    def event(kind: str, seq: int, receive_ns: int, *, bids=(), asks=()) -> OrderBookEvent:
        return OrderBookEvent(
            event_id=f"evt-{seq}",
            venue="coinbase",
            symbol="BTC/USD",
            event_type=kind,
            sequence=seq,
            sequence_start=None,
            provider_ts_ms=None,
            exchange_ts_ms=None,
            local_receive_ns=receive_ns,
            local_receive_wall_ns=receive_ns,
            bids=tuple(bids),
            asks=tuple(asks),
            raw_source="websocket",
        )

    def test_snapshot_then_contiguous_delta_emits_eligible_view(self) -> None:
        self.sync.on_event(self.event(
            "snapshot", 41, 10_000_000,
            bids=(OrderBookLevel(100, 2),),
            asks=(OrderBookLevel(101, 3),),
        ))
        self.sync.on_event(self.event(
            "delta", 42, 20_000_000,
            bids=(OrderBookLevel(100, 4),),
        ))
        view = self.views[-1]
        self.assertEqual(view.status, "SYNCED")
        self.assertTrue(view.eligible)
        self.assertEqual(view.sequence, 42)
        self.assertEqual(view.bids[0].quantity, 4)

    def test_sequence_gap_invalidates_and_clears_previous_book(self) -> None:
        self.sync.on_event(self.event(
            "snapshot", 41, 10_000_000,
            bids=(OrderBookLevel(100, 2),),
            asks=(OrderBookLevel(101, 3),),
        ))
        self.sync.on_event(self.event(
            "delta", 43, 20_000_000,
            bids=(OrderBookLevel(100, 4),),
        ))
        view = self.views[-1]
        self.assertEqual(view.status, "INVALID")
        self.assertFalse(view.eligible)
        self.assertEqual(view.reason, "invalid_sequence_or_book")
        self.assertEqual(view.bids, ())
        self.assertEqual(view.asks, ())

    def test_disconnect_invalidates_until_new_snapshot(self) -> None:
        self.sync.on_event(self.event(
            "snapshot", 41, 10_000_000,
            bids=(OrderBookLevel(100, 2),),
            asks=(OrderBookLevel(101, 3),),
        ))
        self.sync.connection_lost()
        view = self.views[-1]
        self.assertEqual(view.status, "INVALID")
        self.assertEqual(view.reason, "connection_lost")
        self.assertFalse(view.eligible)
        self.assertEqual(view.bids, ())
        self.sync.on_event(self.event(
            "delta", 42, 20_000_000,
            bids=(OrderBookLevel(100, 4),),
        ))
        self.assertEqual(self.views[-1].status, "INVALID")
        self.sync.on_event(self.event(
            "snapshot", 50, 30_000_000,
            bids=(OrderBookLevel(99, 2),),
            asks=(OrderBookLevel(102, 3),),
        ))
        self.assertTrue(self.views[-1].eligible)

    def test_read_time_freshness_expires_without_new_event(self) -> None:
        self.sync.on_event(self.event(
            "snapshot", 41, 10_000_000,
            bids=(OrderBookLevel(100, 2),),
            asks=(OrderBookLevel(101, 3),),
        ))
        fresh = self.sync.snapshot(500_000_000)
        stale = self.sync.snapshot(2_000_000_000)
        self.assertTrue(fresh.eligible)
        self.assertFalse(stale.eligible)
        self.assertEqual(stale.reason, "stale")
        self.assertEqual(stale.sequence, 41)

    def test_crossed_or_one_sided_book_is_not_eligible(self) -> None:
        self.sync.on_event(self.event(
            "snapshot", 41, 10_000_000,
            bids=(OrderBookLevel(102, 2),),
            asks=(OrderBookLevel(101, 3),),
        ))
        self.assertFalse(self.views[-1].eligible)
        self.assertEqual(self.views[-1].reason, "crossed_book")


    def test_duplicate_sequence_fails_closed_and_clears_previous_book(self) -> None:
        self.sync.on_event(self.event(
            "snapshot", 41, 10_000_000,
            bids=(OrderBookLevel(100, 2),),
            asks=(OrderBookLevel(101, 3),),
        ))
        self.sync.on_event(self.event(
            "delta", 42, 20_000_000,
            bids=(OrderBookLevel(100, 4),),
        ))
        self.assertTrue(self.views[-1].eligible)

        # Replaying the same sequence must not leave the last eligible view live.
        self.sync.on_event(self.event(
            "delta", 42, 30_000_000,
            bids=(OrderBookLevel(100, 5),),
        ))
        view = self.views[-1]
        self.assertEqual(view.status, "INVALID")
        self.assertFalse(view.eligible)
        self.assertEqual(view.reason, "invalid_sequence_or_book")
        self.assertEqual(view.bids, ())
        self.assertEqual(view.asks, ())

    def test_out_of_order_sequence_fails_closed_and_clears_previous_book(self) -> None:
        self.sync.on_event(self.event(
            "snapshot", 41, 10_000_000,
            bids=(OrderBookLevel(100, 2),),
            asks=(OrderBookLevel(101, 3),),
        ))
        self.sync.on_event(self.event(
            "delta", 43, 20_000_000,
            bids=(OrderBookLevel(100, 4),),
        ))
        view = self.views[-1]
        self.assertEqual(view.status, "INVALID")
        self.assertFalse(view.eligible)
        self.assertEqual(view.reason, "invalid_sequence_or_book")
        self.assertEqual(view.bids, ())
        self.assertEqual(view.asks, ())


    def test_monotonic_clock_regression_fails_closed(self) -> None:
        self.sync.on_event(self.event(
            "snapshot", 41, 100_000_000,
            bids=(OrderBookLevel(100, 2),),
            asks=(OrderBookLevel(101, 3),),
        ))
        self.assertTrue(self.views[-1].eligible)

        # A caller with a regressed monotonic timestamp must not turn a
        # future observation into an age-zero eligible book.
        view = self.sync.snapshot(99_000_000)
        self.assertEqual(view.status, "SYNCED")
        self.assertFalse(view.eligible)
        self.assertIsNone(view.age_ms)
        self.assertEqual(view.reason, "clock_regression")


if __name__ == "__main__":
    unittest.main()
