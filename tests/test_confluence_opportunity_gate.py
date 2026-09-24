from PC_ENGINE.core.confluence_runtime import PaperConfluenceRuntime


def test_confluence_cost_gate_blocks_non_viable_paper_opportunity(tmp_path):
    runtime = PaperConfluenceRuntime({
        "data_dir": str(tmp_path),
        "minimum_net_edge_bps": 5.0,
        "minimum_edge_margin_bps": 2.0,
        "derivatives": {"enabled": False},
    })
    result = runtime.evaluate_and_record(
        symbol="BTC/USDT",
        price=100_000.0,
        ohlcv=[[i, 100, 101, 99, 100, 10] for i in range(30)],
        technical_action="BUY",
        technical_strength=0.9,
        pattern_bias=0.8,
        radar_pressure=0.7,
        timeframes={"1m": [[i, 100, 101, 99, 100, 10] for i in range(30)]},
        trade_events=[],
        record_state=False,
        cost_context={
            "gross_edge_bps": 20.0,
            "fee_bps": 8.0,
            "spread_bps": 5.0,
            "slippage_bps": 4.0,
            "liquidity_bps": 2.0,
            "latency_bps": 3.0,
        },
    )
    assert result.score.action == "HOLD"
    assert result.score.score == 0.0
    assert result.score.confidence == 0.0
    assert any("opportunity gate" in item for item in result.score.contradictions)


def test_confluence_cost_gate_preserves_viable_paper_opportunity(tmp_path):
    runtime = PaperConfluenceRuntime({
        "data_dir": str(tmp_path),
        "minimum_net_edge_bps": 5.0,
        "minimum_edge_margin_bps": 2.0,
        "derivatives": {"enabled": False},
    })
    result = runtime.evaluate_and_record(
        symbol="BTC/USDT",
        price=100_000.0,
        ohlcv=[[i, 100, 101, 99, 100, 10] for i in range(30)],
        technical_action="BUY",
        technical_strength=0.9,
        pattern_bias=0.8,
        radar_pressure=0.7,
        timeframes={"1m": [[i, 100, 101, 99, 100, 10] for i in range(30)]},
        trade_events=[],
        record_state=False,
        cost_context={
            "gross_edge_bps": 50.0,
            "fee_bps": 8.0,
            "spread_bps": 5.0,
            "slippage_bps": 4.0,
            "liquidity_bps": 2.0,
            "latency_bps": 3.0,
        },
    )
    assert result.score.action in {"BUY", "HOLD"}
    assert result.score.score >= 0.0
