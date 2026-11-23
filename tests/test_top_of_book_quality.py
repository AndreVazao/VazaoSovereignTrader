from __future__ import annotations

import unittest
from types import SimpleNamespace

from PC_ENGINE.market_events.top_of_book_quality import TopOfBookQualityGate


class TopOfBookQualityGateTests(unittest.TestCase):
    def event(self, *, ts=1000, bid=100.0, ask=101.0, receive_ns=1_000_000_000):
        return SimpleNamespace(
            venue="binance",
            symbol="BTC/USDT",
            bid=bid,
            ask=ask,
            provider_ts_ms=ts,
            local_receive_ns=receive_ns,
            local_receive_wall_ns=1_700_000_000_000_000_000,
        )

    def test_accepts_first_ordered_provider_observation(self):
        gate = TopOfBookQualityGate()
        accepted, quality = gate.evaluate(self.event(), now_monotonic_ns=1_100_000_000)
        self.assertTrue(accepted)
        self.assertEqual(quality, "PROVIDER_TIMESTAMP_ORDERED")

    def test_rejects_duplicate_provider_timestamp_and_quote(self):
        gate = TopOfBookQualityGate()
        gate.evaluate(self.event(), now_monotonic_ns=1_100_000_000)
        accepted, reason = gate.evaluate(self.event(), now_monotonic_ns=1_200_000_000)
        self.assertFalse(accepted)
        self.assertEqual(reason, "DUPLICATE_PROVIDER_OBSERVATION")
        self.assertEqual(gate.snapshot()["rejected_duplicate_provider_observation"], 1)

    def test_rejects_out_of_order_provider_timestamp(self):
        gate = TopOfBookQualityGate()
        gate.evaluate(self.event(ts=1002), now_monotonic_ns=1_100_000_000)
        accepted, reason = gate.evaluate(self.event(ts=1001), now_monotonic_ns=1_200_000_000)
        self.assertFalse(accepted)
        self.assertEqual(reason, "OUT_OF_ORDER_PROVIDER_TIMESTAMP")

    def test_keeps_equal_timestamp_quote_change_but_marks_ambiguity(self):
        gate = TopOfBookQualityGate()
        gate.evaluate(self.event(), now_monotonic_ns=1_100_000_000)
        accepted, quality = gate.evaluate(
            self.event(bid=100.5, ask=101.5), now_monotonic_ns=1_200_000_000
        )
        self.assertTrue(accepted)
        self.assertEqual(quality, "SAME_TIMESTAMP_DIFFERENT_QUOTE")
        self.assertEqual(gate.snapshot()["same_timestamp_different_quote"], 1)

    def test_missing_provider_timestamp_is_explicit_not_fabricated(self):
        gate = TopOfBookQualityGate()
        accepted, quality = gate.evaluate(self.event(ts=None), now_monotonic_ns=1_100_000_000)
        self.assertTrue(accepted)
        self.assertEqual(quality, "LOCAL_RECEIVE_ONLY")
        self.assertEqual(gate.snapshot()["provider_timestamp_missing"], 1)

    def test_rejects_invalid_or_crossed_quotes(self):
        gate = TopOfBookQualityGate()
        for event in (self.event(bid=0), self.event(bid=102, ask=101), self.event(bid=float("nan"))):
            accepted, _ = gate.evaluate(event, now_monotonic_ns=1_100_000_000)
            self.assertFalse(accepted)

    def test_rejects_stale_local_receive_clock(self):
        gate = TopOfBookQualityGate()
        accepted, reason = gate.evaluate(
            self.event(), now_monotonic_ns=40_000_000_000
        )
        self.assertFalse(accepted)
        self.assertEqual(reason, "REJECTED_INVALID_RECEIVE_CLOCK")


if __name__ == "__main__":
    unittest.main()
