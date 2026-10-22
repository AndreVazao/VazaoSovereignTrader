from __future__ import annotations

import unittest

from PC_ENGINE.market_events.binance_book_state import BinanceSpotDepthBook, BookStatus
from PC_ENGINE.market_events.orderbook import OrderBookEvent, OrderBookLevel


class BinanceSpotDepthBookTests(unittest.TestCase):
    def event(self, start: int, end: int, *, bids=(), asks=(), receive_ns=10_000_000):
        return OrderBookEvent(
            event_id=f"evt-{start}-{end}",
            venue="binance",
            symbol="BTC/USDT",
            event_type="delta",
            sequence=end,
            sequence_start=start,
            provider_ts_ms=1_700_000_000_000,
            exchange_ts_ms=1_700_000_000_000,
            local_receive_ns=receive_ns,
            local_receive_wall_ns=1_700_000_000_000_000_000,
            bids=tuple(OrderBookLevel(*level) for level in bids),
            asks=tuple(OrderBookLevel(*level) for level in asks),
            raw_source="test",
        )

    def book(self, max_age_ms=1000):
        return BinanceSpotDepthBook("BTC/USDT", max_age_ms=max_age_ms, max_levels=5)

    def install_valid_snapshot(self, book, update_id=100, bids=((100.0, 2.0),), asks=((101.0, 3.0),)):
        return book.install_snapshot(
            update_id,
            tuple(OrderBookLevel(*level) for level in bids),
            tuple(OrderBookLevel(*level) for level in asks),
        )

    def test_snapshot_alone_is_not_eligible_until_contiguous_delta(self):
        book = self.book()
        self.assertTrue(self.install_valid_snapshot(book))
        self.assertFalse(book.snapshot(now_ns=10_000_000).eligible)
        self.assertTrue(book.apply_delta(self.event(
            101, 103, bids=((100.0, 4.0),), asks=((101.0, 0.0), (102.0, 1.0))
        )))
        view = book.snapshot(now_ns=20_000_000)
        self.assertEqual(view.status, BookStatus.SYNCED)
        self.assertTrue(view.eligible)
        self.assertEqual(view.update_id, 103)
        self.assertEqual(view.bids[0].quantity, 4.0)
        self.assertEqual([level.price for level in view.asks], [102.0])

    def test_old_or_duplicate_delta_is_ignored(self):
        book = self.book()
        self.install_valid_snapshot(book)
        self.assertTrue(book.apply_delta(self.event(99, 101, receive_ns=5_000_000)))
        self.assertEqual(book.update_id, 101)
        self.assertFalse(book.apply_delta(self.event(100, 101, bids=((100.0, 9.0),))))
        self.assertEqual(book.update_id, 101)
        self.assertEqual(book.bids[100.0], 2.0)

    def test_sequence_gap_invalidates_and_clears_book(self):
        book = self.book()
        self.install_valid_snapshot(book)
        self.assertTrue(book.apply_delta(self.event(101, 103)))
        self.assertFalse(book.apply_delta(self.event(105, 106)))
        view = book.snapshot(now_ns=20_000_000)
        self.assertEqual(view.status, BookStatus.INVALID)
        self.assertFalse(view.eligible)
        self.assertEqual(view.reason, "sequence_gap")
        self.assertEqual(view.bids, ())
        self.assertEqual(view.asks, ())

    def test_stale_book_is_not_eligible(self):
        book = self.book(max_age_ms=50)
        self.install_valid_snapshot(book, update_id=10)
        book.apply_delta(self.event(11, 11, receive_ns=1_000_000))
        view = book.snapshot(now_ns=100_000_000)
        self.assertFalse(view.eligible)
        self.assertEqual(view.reason, "stale")

    def test_invalid_snapshot_and_missing_sequence_fail_closed(self):
        book = self.book()
        self.assertFalse(book.install_snapshot(
            100, (OrderBookLevel(float("nan"), 1.0),), (OrderBookLevel(101.0, 1.0),)
        ))
        self.assertEqual(book.status, BookStatus.INVALID)
        self.install_valid_snapshot(book)
        malformed = self.event(101, 101)
        malformed = OrderBookEvent(**{**malformed.__dict__, "sequence_start": None})
        self.assertFalse(book.apply_delta(malformed))
        self.assertEqual(book.status, BookStatus.INVALID)

    def test_negative_or_reversed_sequence_range_invalidates(self):
        for start, end in ((-1, 101), (101, -1), (103, 102)):
            with self.subTest(start=start, end=end):
                book = self.book()
                self.install_valid_snapshot(book)
                self.assertFalse(book.apply_delta(self.event(start, end)))
                self.assertEqual(book.status, BookStatus.INVALID)
                self.assertEqual(book.snapshot(now_ns=20_000_000).reason, "invalid_sequence_range")

    def test_crossed_book_is_not_eligible(self):
        book = self.book()
        self.install_valid_snapshot(book, bids=((101.0, 2.0),), asks=((101.0, 3.0),))
        self.assertTrue(book.apply_delta(self.event(101, 101)))
        view = book.snapshot(now_ns=20_000_000)
        self.assertFalse(view.eligible)
        self.assertEqual(view.reason, "crossed_book")

    def test_non_finite_age_configuration_is_rejected(self):
        for age in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(age=age):
                with self.assertRaises(ValueError):
                    BinanceSpotDepthBook("BTC/USDT", max_age_ms=age)


if __name__ == "__main__":
    unittest.main()
