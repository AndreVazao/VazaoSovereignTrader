from PC_ENGINE.core.confluence_runtime import PaperConfluenceRuntime
from PC_ENGINE.core.risk import RiskEngine


def test_risk_engine_authorizes_valid_signal():
    engine = RiskEngine({})
    decision = engine.authorize_signal("BTC/USDT", "BUY", now=100.0)
    assert decision.authorized is True
    assert decision.reason == "risk engine authorized"


def test_risk_engine_blocks_global_drawdown():
    engine = RiskEngine({"max_daily_loss_pct": -0.01})
    engine.state.pnl_today_pct = -0.02
    decision = engine.authorize_signal("BTC/USDT", "BUY", now=100.0)
    assert decision.authorized is False
    assert "daily drawdown" in decision.reason


def test_risk_engine_blocks_symbol_loss_streak():
    engine = RiskEngine({"max_symbol_loss_streak": 2})
    engine.state.symbol_loss_streak["BTC/USDT"] = 2
    decision = engine.authorize_signal("BTC/USDT", "SELL", now=100.0)
    assert decision.authorized is False
    assert "loss streak" in decision.reason


def _runtime(tmp_path, risk=None):
    return PaperConfluenceRuntime({
        "data_dir": str(tmp_path),
        "minimum_net_edge_bps": 5.0,
        "minimum_edge_margin_bps": 2.0,
        "derivatives": {"enabled": False},
        "risk": risk or {},
    })


def _kwargs():
    return {
        "symbol": "BTC/USDT",
        "price": 100_000.0,
        "ohlcv": [[i, 100, 101, 99, 100, 10] for i in range(30)],
        "technical_action": "BUY",
        "technical_strength": 0.9,
        "pattern_bias": 0.8,
        "radar_pressure": 0.7,
        "timeframes": {"1m": [[i, 100, 101, 99, 100, 10] for i in range(30)]},
        "trade_events": [],
        "record_state": False,
        "cost_context": {
            "gross_edge_bps": 50.0,
            "fee_bps": 8.0,
            "spread_bps": 5.0,
            "slippage_bps": 4.0,
            "liquidity_bps": 2.0,
            "latency_bps": 3.0,
        },
    }


def test_confluence_viable_opportunity_reaches_risk_engine(tmp_path):
    result = _runtime(tmp_path).evaluate_and_record(**_kwargs())
    assert result.risk_authorized is True
    assert result.risk_reason == "risk engine authorized"


def test_confluence_risk_breach_blocks_even_strong_signal(tmp_path):
    runtime = _runtime(tmp_path, {"max_daily_loss_pct": -0.01})
    runtime.risk.state.pnl_today_pct = -0.02
    result = runtime.evaluate_and_record(**_kwargs())
    assert result.risk_authorized is False
    assert result.score.action == "HOLD"
    assert result.score.score == 0.0
    assert any("risk engine" in item for item in result.score.contradictions)


def test_non_viable_opportunity_never_reaches_risk_engine(tmp_path):
    kwargs = _kwargs()
    kwargs["cost_context"]["gross_edge_bps"] = 20.0
    result = _runtime(tmp_path).evaluate_and_record(**kwargs)
    assert result.score.action == "HOLD"
    assert result.risk_authorized is False
    assert result.risk_reason == "not evaluated"
