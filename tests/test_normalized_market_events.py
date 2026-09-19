from __future__ import annotations

import unittest

from PC_ENGINE.market_events.normalized import MarketEventFactory


class NormalizedMarketEventTests(unittest.TestCase):
    def test_preserves_timing_chain_without_using_browser_as_authority(self) -> None:
        event = MarketEventFactory.create(
            venue="okx",
            symbol="BTC/USDT",
            event_type="ticker",
            provider_ts_ms=1000,
            exchange_ts_ms=1000,
            receive_ns=2_000_000_000,
            receive_wall_ns=1_700_000_000_000_000_000,
            process_ns=2_000_250_000,
            browser_render_ns=2_010_000_000,
            price=100.5,
            raw_source="websocket",
        )
        self.assertEqual(event.provider_ts_ms, 1000)
        self.assertEqual(event.exchange_ts_ms, 1000)
        self.assertEqual(event.processing_delay_ns, 250_000)
        self.assertEqual(event.local_receive_wall_ns, 1_700_000_000_000_000_000)
        self.assertEqual(event.browser_render_ns, 2_010_000_000)
        self.assertNotEqual(event.local_receive_ns, event.browser_render_ns)

    def test_rejects_invalid_local_timing(self) -> None:
        with self.assertRaises(ValueError):
            MarketEventFactory.create(
                venue="binance",
                symbol="BTC/USDT",
                event_type="trade",
                receive_ns=20,
                process_ns=19,
            )


if __name__ == "__main__":
    unittest.main()
