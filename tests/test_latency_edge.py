from PC_ENGINE.radar.latency_edge import LatencyEdgeDetector


def test_latency_edge_requires_statistical_history_and_positive_net_edge():
    detector = LatencyEdgeDetector(
        min_samples=3,
        min_lead_bps=2.0,
        fee_bps=1.0,
        spread_bps=0.5,
        slippage_bps=0.5,
        execution_latency_ms=0,
    )
    result = None
    for _ in range(3):
        result = detector.observe(
            symbol="BTC/USDT",
            leader="binance",
            follower="okx",
            direction="UP",
            lead_ms=25,
            leader_move_bps=6.0,
            follower_move_bps=5.0,
        )

    assert result is not None
    assert result.sample_count == 3
    assert result.same_direction_ratio == 1.0
    assert result.persistence_ratio == 1.0
    assert result.net_expected_edge_bps == 4.0
    assert result.eligible is True


def test_latency_edge_rejects_stale_or_unprofitable_leads():
    detector = LatencyEdgeDetector(
        min_samples=1,
        max_lead_ms=100,
        min_lead_bps=2.0,
        fee_bps=4.0,
        spread_bps=2.0,
        slippage_bps=2.0,
    )
    stale = detector.observe(
        symbol="ETH/USDT",
        leader="binance",
        follower="coinbase",
        direction="DOWN",
        lead_ms=150,
        leader_move_bps=-10.0,
        follower_move_bps=-9.0,
    )
    assert stale.eligible is False

    costly = detector.observe(
        symbol="ETH/USDT",
        leader="binance",
        follower="coinbase",
        direction="DOWN",
        lead_ms=20,
        leader_move_bps=-5.0,
        follower_move_bps=-4.0,
    )
    assert costly.net_expected_edge_bps < 0
    assert costly.eligible is False


def test_latency_edge_tracks_directional_persistence():
    detector = LatencyEdgeDetector(min_samples=4, min_same_direction_ratio=0.75)
    for leader_bps, follower_bps in ((5, 4), (5, 4), (5, 4), (-5, 4)):
        result = detector.observe(
            symbol="SOL/USDT",
            leader="okx",
            follower="binance",
            direction="UP",
            lead_ms=30,
            leader_move_bps=leader_bps,
            follower_move_bps=follower_bps,
        )

    assert result.same_direction_ratio == 0.75
    assert result.eligible is False
