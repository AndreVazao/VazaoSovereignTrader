from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from PC_ENGINE.opportunity.capital_opportunity import CapitalOpportunityEngine


class CapitalOpportunityTests(unittest.TestCase):
    def test_requires_minimum_sample_count(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            observations = Path(tmp) / "observations.jsonl"
            observations.write_text(
                json.dumps(
                    {
                        "lead_lag": [
                            {
                                "symbol": "BTC/USDT",
                                "leader": "okx",
                                "follower": "binance",
                                "direction": "UP",
                                "lag_ms": 20,
                                "follower_return_pct": 0.03,
                            }
                        ]
                    }
                ) + "\n",
                encoding="utf-8",
            )
            engine = CapitalOpportunityEngine(
                observations,
                Path(tmp) / "out.jsonl",
                min_samples=2,
            )
            self.assertEqual(engine.analyze(), [])

    def test_marks_net_positive_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            observations = Path(tmp) / "observations.jsonl"
            events = [
                {
                    "symbol": "BTC/USDT",
                    "leader": "okx",
                    "follower": "binance",
                    "direction": "UP",
                    "lag_ms": 25,
                    "follower_return_pct": 0.20,
                }
                for _ in range(10)
            ]
            observations.write_text(
                json.dumps({"lead_lag": events}) + "\n",
                encoding="utf-8",
            )
            engine = CapitalOpportunityEngine(
                observations,
                Path(tmp) / "out.jsonl",
                min_samples=5,
                fee_bps=2,
                spread_bps=1,
                slippage_bps=1,
                latency_buffer_bps=1,
                min_net_edge_bps=5,
                default_required_capital=100,
            )
            candidates = engine.analyze()
            self.assertEqual(len(candidates), 1)
            self.assertEqual(candidates[0].status, "CANDIDATE")
            self.assertGreater(candidates[0].estimated_net_edge_bps, 0)

    def test_costs_can_turn_candidate_into_watch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            observations = Path(tmp) / "observations.jsonl"
            events = [
                {
                    "symbol": "ETH/USDT",
                    "leader": "coinbase",
                    "follower": "bybit",
                    "direction": "DOWN",
                    "lag_ms": 100,
                    "follower_return_pct": 0.02,
                }
                for _ in range(5)
            ]
            observations.write_text(
                json.dumps({"lead_lag": events}) + "\n",
                encoding="utf-8",
            )
            engine = CapitalOpportunityEngine(
                observations,
                Path(tmp) / "out.jsonl",
                min_samples=5,
                fee_bps=10,
                spread_bps=5,
                slippage_bps=5,
                latency_buffer_bps=5,
                min_net_edge_bps=2,
            )
            candidates = engine.analyze()
            self.assertEqual(candidates[0].status, "WATCH")


if __name__ == "__main__":
    unittest.main()
