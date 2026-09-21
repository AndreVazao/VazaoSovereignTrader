from PC_ENGINE.core.shared_intelligence import SharedIntelligenceArtifact
from PC_ENGINE.core.shared_intelligence_aggregator import SharedIntelligenceAggregator, SharedSourceTrustPolicy


def row(node, mean=3.0, trust=0.99):
    payload = SharedIntelligenceArtifact(
        artifact_type="state_outcome", strategy_id="breakout_v1", market="BTC/USDT",
        regime="TREND_UP", horizon_seconds=60, sample_count=100, win_count=60,
        win_rate=0.60, mean_net_bps=mean, median_net_bps=mean - 0.3,
        eligible=True, created_at_ms=1000, source_node_ref=node, trust_score=trust,
        source_count=99,
    ).to_public_dict()
    return {"artifact": payload}


def test_remote_trust_and_source_count_are_not_authoritative():
    agg = SharedIntelligenceAggregator(
        SharedSourceTrustPolicy({"node-a": 0.70, "node-b": 0.70}), min_sources=2
    )
    result = agg.aggregate([row("node-a", trust=0.0), row("node-b", trust=1.0)])[0]
    assert result.source_count == 2
    assert result.aggregate_trust == 0.91


def test_duplicate_source_cannot_amplify_consensus():
    agg = SharedIntelligenceAggregator(SharedSourceTrustPolicy({"node-a": 0.7, "node-b": 0.7}), min_sources=2)
    result = agg.aggregate([row("node-a", 2.0), row("node-a", 20.0), row("node-b", 4.0)])[0]
    assert result.source_count == 2
    assert result.mean_net_bps < 5.0


def test_unknown_source_does_not_enter_consensus():
    agg = SharedIntelligenceAggregator(SharedSourceTrustPolicy({"node-a": 0.7}), min_sources=2)
    assert agg.aggregate([row("node-a"), row("unknown")]) == []
