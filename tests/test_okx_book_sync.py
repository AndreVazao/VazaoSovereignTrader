from __future__ import annotations

import unittest

from PC_ENGINE.market_events.okx_book_sync import OKXBooksSynchronizer
from PC_ENGINE.market_events.orderbook import OrderBookEvent, OrderBookLevel


class OKXBooksSynchronizerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.views = []
        self.sync = OKXBooksSynchronizer("BTC/USDT", self.views.append, max_age_ms=1000)

    @staticmethod
    def event(kind: str, seq: int, receive_ns: int, *, start=None, bids=(), asks=()) -> OrderBookEvent:
        return OrderBookEvent(
            event_id=f"evt-{kind}-{seq}",
            venue="okx",
            symbol="BTC/USDT",
            event_type=kind,
            sequence=seq,
            sequence_start=start,
            provider_ts_ms=None,
            exchange_ts_ms=None,
            local_receive_ns=receive_ns,
            local_receive_wall_ns=receive_ns,
            bids=tuple(bids),
            asks=tuple(asks),
            raw_source="websocket",
        )

    def seed(self) -> None:
        self.sync.on_event(self.event(
            "snapshot", 41, 10_000_000,
            bids=(OrderBookLevel(100, 2),),
            asks=(OrderBookLevel(101, 3),),
        ))
        self.assertTrue(self.views[-1].eligible)

    def test_snapshot_then_exact_prev_sequence_delta_is_eligible(self) -> None:
        self.seed()
        self.sync.on_event(self.event(
            "delta", 43, 20_000_000, start=42,
            bids=(OrderBookLevel(100, 4),),
        ))
        view = self.views[-1]
        self.assertEqual(view.status, "SYNCED")
        self.assertTrue(view.eligible)
        self.assertEqual(view.sequence, 43)
        self.assertEqual(view.bids[0].quantity, 4)

    def test_sequence_gap_clears_previous_book(self) -> None:
        self.seed()
        self.sync.on_event(self.event(
            "delta", 44, 20_000_000, start=43,
            bids=(OrderBookLevel(100, 4),),
        ))
        view = self.views[-1]
        self.assertEqual(view.status, "INVALID")
        self.assertFalse(view.eligible)
        self.assertEqual(view.reason, "sequence_gap")
        self.assertEqual(view.bids, ())
        self.assertEqual(view.asks, ())

    def test_prev_sequence_mismatch_fails_closed_even_if_range_builder_would_accept(self) -> None:
        self.seed()
        # Current is 41, but prevSeqId would be 40 (start=41); this is not
        # the OKX contract even if a generic overlapping-range builder accepts it.
        self.sync.on_event(self.event(
            "delta", 42, 20_000_000, start=41,
            bids=(OrderBookLevel(100, 4),),
        ))
        view = self.views[-1]
        self.assertFalse(view.eligible)
        self.assertEqual(view.reason, "sequence_gap")
        self.assertEqual(view.bids, ())

    def test_duplicate_or_out_of_order_delta_fails_closed(self) -> None:
        self.seed()
        self.sync.on_event(self.event(
            "delta", 42, 20_000_000, start=42,
            bids=(OrderBookLevel(100, 4),),
        ))
        self.assertTrue(self.views[-1].eligible)
        self.sync.on_event(self.event(
            "delta", 42, 30_000_000, start=43,
            bids=(OrderBookLevel(100, 5),),
        ))
        view = self.views[-1]
        self.assertFalse(view.eligible)
        self.assertEqual(view.status, "INVALID")
        self.assertEqual(view.bids, ())

    def test_disconnect_invalidates_until_new_snapshot(self) -> None:
        self.seed()
        self.sync.connection_lost()
        view = self.views[-1]
        self.assertEqual(view.reason, "connection_lost")
        self.assertFalse(view.eligible)
        self.sync.on_event(self.event(
            "delta", 42, 20_000_000, start=42,
            bids=(OrderBookLevel(100, 4),),
        ))
        self.assertFalse(self.views[-1].eligible)
        self.sync.on_event(self.event(
            "snapshot", 50, 30_000_000,
            bids=(OrderBookLevel(99, 2),),
            asks=(OrderBookLevel(102, 3),),
        ))
        self.assertTrue(self.views[-1].eligible)

    def test_stale_or_clock_regressed_view_is_not_eligible(self) -> None:
        self.seed()
        stale = self.sync.snapshot(2_000_000_000)
        self.assertFalse(stale.eligible)
        self.assertEqual(stale.reason, "stale")
        regressed = self.sync.snapshot(9_000_000)
        self.assertFalse(regressed.eligible)
        self.assertIsNone(regressed.age_ms)
        self.assertEqual(regressed.reason, "clock_regression")

    def test_matching_heartbeat_refreshes_freshness_without_mutating_book(self) -> None:
        self.seed()
        self.sync.on_event(self.event("heartbeat", 41, 900_000_000))
        view = self.views[-1]
        self.assertTrue(view.eligible)
        self.assertEqual(view.sequence, 41)
        self.assertEqual(view.bids[0].quantity, 2)
        self.assertEqual(view.observation_time_ns, 900_000_000)

    def test_mismatched_heartbeat_invalidates_book(self) -> None:
        self.seed()
        self.sync.on_event(self.event("heartbeat", 40, 20_000_000))
        view = self.views[-1]
        self.assertFalse(view.eligible)
        self.assertEqual(view.reason, "heartbeat_sequence_mismatch")
        self.assertEqual(view.bids, ())

    def test_older_snapshot_cannot_replace_newer_book(self) -> None:
        self.sync.on_event(self.event(
            "snapshot", 50, 10_000_000,
            bids=(OrderBookLevel(100, 2),),
            asks=(OrderBookLevel(101, 3),),
        ))
        self.assertTrue(self.views[-1].eligible)
        self.sync.on_event(self.event(
            "snapshot", 49, 20_000_000,
            bids=(OrderBookLevel(99, 9),),
            asks=(OrderBookLevel(102, 9),),
        ))
        view = self.views[-1]
        self.assertFalse(view.eligible)
        self.assertEqual(view.reason, "stale_snapshot")
        self.assertEqual(view.bids, ())

    def test_crossed_book_is_not_eligible(self) -> None:
        self.sync.on_event(self.event(
            "snapshot", 41, 10_000_000,
            bids=(OrderBookLevel(102, 2),),
            asks=(OrderBookLevel(101, 3),),
        ))
        self.assertFalse(self.views[-1].eligible)
        self.assertEqual(self.views[-1].reason, "crossed_book")


if __name__ == "__main__":
    unittest.main()
