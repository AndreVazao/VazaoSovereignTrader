from PC_ENGINE.radar.external_source_latency import ExternalSourceLatencyProfiler


def test_external_source_latency_profile_detects_research_edge():
    profiler = ExternalSourceLatencyProfiler(
        min_samples=3,
        min_lead_ms=20,
        max_lead_ms=500,
        min_same_direction_ratio=0.66,
        fee_bps=2,
        spread_bps=1,
        slippage_bps=1,
        execution_buffer_bps=1,
    )
    for i in range(3):
        profiler.record(
            source_id="source-a",
            symbol="BTC/USDT",
            source_ts_ms=1_000 + i * 1_000,
            source_price=100.0,
            market_ts_ms=1_080 + i * 1_000,
            market_price=100.08,
            direction="UP",
            observed_ts_ms=2_000 + i,
        )

    profile = profiler.profile("source-a", "BTC/USDT", "UP")

    assert profile.samples == 3
    assert profile.median_lead_ms == 80
    assert profile.same_direction_ratio == 1.0
    assert profile.net_edge_bps > 0
    assert profile.eligible is True


def test_external_source_latency_rejects_non_leading_source():
    profiler = ExternalSourceLatencyProfiler(min_samples=1, min_lead_ms=20, max_lead_ms=500)
    profiler.record(
        source_id="source-b",
        symbol="ETH/USDT",
        source_ts_ms=2_000,
        source_price=100.0,
        market_ts_ms=1_990,
        market_price=100.02,
        direction="UP",
    )

    profile = profiler.profile("source-b", "ETH/USDT", "UP")

    assert profile.samples == 0
    assert profile.eligible is False
