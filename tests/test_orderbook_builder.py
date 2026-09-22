from __future__ import annotations

import unittest

from PC_ENGINE.market_events.orderbook import OrderBookEvent, OrderBookLevel
from PC_ENGINE.market_events.orderbook_builder import OrderBookBuilder


class OrderBookBuilderTests(unittest.TestCase):
    def event(self, kind: str, seq: int, bids=(), asks=()):
        return OrderBookEvent(
            event_id=str(seq),
            venue="test",
            symbol="BTC/USDT",
            event_type=kind,
            sequence=seq,
            sequence_start=seq,
            provider_ts_ms=seq,
            exchange_ts_ms=seq,
            local_receive_ns=seq,
            local_receive_wall_ns=seq,
            bids=tuple(bids),
            asks=tuple(asks),
            raw_source="test",
        )

    def test_snapshot_then_delta(self) -> None:
        builder = OrderBookBuilder("test", "BTC/USDT")
        self.assertIsNone(builder.apply(self.event(
            "delta", 2, bids=(OrderBookLevel(100, 1),))))
        book = builder.apply(self.event(
            "snapshot", 10,
            bids=(OrderBookLevel(100, 2), OrderBookLevel(99, 1)),
            asks=(OrderBookLevel(101, 3),)))
        self.assertEqual(book.best_bid, 100)
        book = builder.apply(self.event(
            "delta", 11,
            bids=(OrderBookLevel(100, 0), OrderBookLevel(98, 4)),
            asks=(OrderBookLevel(101, 2),)))
        self.assertEqual(book.best_bid, 99)
        self.assertEqual(book.bids[0].quantity, 1)
        self.assertEqual(book.asks[0].quantity, 2)

    def test_sequence_gap_stales_book(self) -> None:
        builder = OrderBookBuilder("test", "BTC/USDT")
        builder.apply(self.event("snapshot", 10, bids=(OrderBookLevel(100, 1),)))
        self.assertIsNone(builder.apply(self.event("delta", 12, bids=(OrderBookLevel(101, 1),))))
        self.assertTrue(builder.stale)

    def test_old_sequence_stales_book(self) -> None:
        builder = OrderBookBuilder("test", "BTC/USDT")
        builder.apply(self.event("snapshot", 10, bids=(OrderBookLevel(100, 1),)))
        self.assertIsNone(builder.apply(self.event("delta", 10, bids=(OrderBookLevel(101, 1),))))
        self.assertTrue(builder.stale)


if __name__ == "__main__":
    unittest.main()
