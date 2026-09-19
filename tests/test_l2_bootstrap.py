from __future__ import annotations

import unittest

from PC_ENGINE.market_events.l2_bootstrap import BinanceDepthSnapshot, BinanceL2Bootstrapper
from PC_ENGINE.market_events.orderbook import OrderBookEvent, OrderBookLevel


class FakeSnapshotClient:
    def fetch(self, symbol: str, limit: int = 1000) -> BinanceDepthSnapshot:
        return BinanceDepthSnapshot(
            symbol=symbol,
            last_update_id=100,
            bids=(OrderBookLevel(100, 1),),
            asks=(OrderBookLevel(101, 1),),
        )


class L2BootstrapTests(unittest.TestCase):
    def delta(self, start: int, end: int) -> OrderBookEvent:
        return OrderBookEvent(
            event_id=f"{start}-{end}",
            venue="binance",
            symbol="BTC/USDT",
            event_type="delta",
            sequence=end,
            sequence_start=start,
            provider_ts_ms=end,
            exchange_ts_ms=end,
            local_receive_ns=end,
            local_receive_wall_ns=end,
            bids=(OrderBookLevel(100, 2),),
            asks=(),
            raw_source="websocket",
        )

    def test_bootstrap_from_snapshot_and_buffer(self) -> None:
        builder, book = BinanceL2Bootstrapper(FakeSnapshotClient()).bootstrap(
            "BTC/USDT",
            [self.delta(90, 99), self.delta(101, 102)],
        )
        self.assertTrue(builder.initialized)
        self.assertEqual(book.sequence, 102)
        self.assertEqual(book.bids[0].quantity, 2)

    def test_gap_after_bootstrap_requires_resync(self) -> None:
        builder, book = BinanceL2Bootstrapper(FakeSnapshotClient()).bootstrap(
            "BTC/USDT",
            [self.delta(101, 102), self.delta(104, 105)],
        )
        self.assertIsNone(book)
        self.assertTrue(builder.stale)


if __name__ == "__main__":
    unittest.main()
