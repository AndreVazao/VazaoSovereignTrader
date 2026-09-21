from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from PC_ENGINE.core.opportunity import PaperOpportunityEngine
from PC_ENGINE.radar.external_source_latency import ExternalSourceLatencyProfiler
from PC_ENGINE.radar.websocket_radar import MarketEvent, WebSocketMarketRadar


class ExternalLatencyIntegrationTests(unittest.TestCase):
    def test_radar_records_external_source_against_reference_market(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "external.jsonl"
            profiler = ExternalSourceLatencyProfiler(
                min_samples=1,
                min_lead_ms=25,
                max_lead_ms=2000,
                path=path,
            )
            radar = WebSocketMarketRadar(
                ["BTC/USDT"],
                exchanges=[],
                data_dir=Path(tmp),
                external_latency_profiler=profiler,
            )
            radar._emit(
                MarketEvent(
                    "binance", "BTC/USDT", 100.10, 1.0, "BUY",
                    1_100, 1_101, 1, 100.00,
                )
            )
            observation = radar.record_external_source(
                source_id="official-feed",
                symbol="BTC/USDT",
                source_ts_ms=1_000,
                source_price=100.00,
                direction="UP",
                observed_ts_ms=1_200,
            )
            self.assertIsNotNone(observation)
            assert observation is not None
            self.assertEqual(observation.lead_ms, 100)
            profile = profiler.profile("official-feed", "BTC/USDT", "UP")
            self.assertTrue(profile.eligible)
            self.assertGreater(profile.net_edge_bps, 0.0)

            reloaded = ExternalSourceLatencyProfiler(
                min_samples=1,
                min_lead_ms=25,
                max_lead_ms=2000,
                path=path,
            )
            self.assertEqual(
                reloaded.profile("official-feed", "BTC/USDT", "UP").samples,
                1,
            )

    def test_opportunity_uses_fresh_external_latency_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            profile_path = Path(tmp) / "external_source_latency_profiles.jsonl"
            profile_path.write_text(
                '{"source_id":"official-feed","symbol":"BTC/USDT","direction":"UP",'
                '"samples":50,"median_lead_ms":100,"p25_lead_ms":80,"p75_lead_ms":120,'
                '"mean_delta_bps":10,"median_delta_bps":10,"same_direction_ratio":0.9,'
                '"net_edge_bps":3,"eligible":true,"observed_ts_ms":1000000}\n',
                encoding="utf-8",
            )
            engine = PaperOpportunityEngine({
                "external_latency_profile_path": str(profile_path),
                "external_latency_weight": 0.10,
                "external_latency_max_bonus": 0.10,
                "external_latency_stale_after_ms": 2000,
                "external_latency_min_edge_bps": 1.0,
            })
            score = engine.score(
                symbol="BTC/USDT",
                strategy_score=0.60,
                action="BUY",
                spread_pct=0.0,
                state=None,
                now_ms=1000500,
            )
            self.assertGreater(score.external_latency_bonus, 0.0)
            self.assertEqual(score.external_latency_edge_bps, 3.0)
            self.assertGreater(score.score, 0.60)


if __name__ == "__main__":
    unittest.main()
