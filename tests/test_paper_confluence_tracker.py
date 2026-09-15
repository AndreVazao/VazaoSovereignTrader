from PC_ENGINE.core.confluence import ConfluenceEngine
from PC_ENGINE.core.paper_confluence_tracker import PaperConfluenceTracker


def test_tracker_records_and_scores(tmp_path):
    tracker = PaperConfluenceTracker(tmp_path, horizons_ms=(1000,))
    score = ConfluenceEngine().evaluate(
        symbol="BTC/USDT",
        technical_action="BUY",
        technical_strength=0.8,
        pattern_bias=0.8,
        radar_pressure=0.7,
    )
    tracker.record("BTC/USDT", 100_000.0, score)
    observations = tracker.observations()
    assert len(observations) == 1
    outcome = tracker.record_outcome(observations[0], 100_500.0)
    assert outcome is not None
    assert outcome["net_bps"] > 0
    report = tracker.summary()
    assert report["stats"][0]["samples"] == 1
