from PC_ENGINE.core.risk import RiskEngine


def test_authorize_order_accepts_within_all_risk_limits():
    engine = RiskEngine({"risk_per_trade_pct": 0.01})
    decision = engine.authorize_order(
        "BTC/USDT",
        "BUY",
        equity=1000.0,
        proposed_notional=100.0,
        current_exposure=100.0,
        current_symbol_exposure=0.0,
        current_open_positions=1,
        max_open_positions=2,
        max_total_exposure_pct=0.35,
        max_symbol_exposure_pct=0.25,
        stop_pct=0.02,
        now=100.0,
    )
    assert decision.authorized is True


def test_authorize_order_blocks_total_exposure():
    engine = RiskEngine({})
    decision = engine.authorize_order(
        "BTC/USDT",
        "BUY",
        equity=1000.0,
        proposed_notional=100.0,
        current_exposure=260.0,
        current_symbol_exposure=0.0,
        current_open_positions=1,
        max_open_positions=2,
        max_total_exposure_pct=0.35,
        max_symbol_exposure_pct=0.25,
        stop_pct=0.01,
        now=100.0,
    )
    assert decision.authorized is False
    assert decision.reason == "total exposure limit reached"


def test_authorize_order_blocks_symbol_exposure():
    engine = RiskEngine({})
    decision = engine.authorize_order(
        "BTC/USDT",
        "BUY",
        equity=1000.0,
        proposed_notional=60.0,
        current_exposure=100.0,
        current_symbol_exposure=200.0,
        current_open_positions=1,
        max_open_positions=2,
        max_total_exposure_pct=0.35,
        max_symbol_exposure_pct=0.25,
        stop_pct=0.01,
        now=100.0,
    )
    assert decision.authorized is False
    assert decision.reason == "BTC/USDT exposure limit reached"


def test_authorize_order_blocks_per_trade_risk_cap():
    engine = RiskEngine({"risk_per_trade_pct": 0.01})
    decision = engine.authorize_order(
        "BTC/USDT",
        "BUY",
        equity=1000.0,
        proposed_notional=120.0,
        current_exposure=0.0,
        current_symbol_exposure=0.0,
        current_open_positions=0,
        max_open_positions=2,
        max_total_exposure_pct=0.35,
        max_symbol_exposure_pct=0.25,
        stop_pct=0.02,
        now=100.0,
    )
    assert decision.authorized is False
    assert decision.reason == "per-trade risk cap exceeded"


def test_authorize_order_blocks_invalid_stop():
    engine = RiskEngine({})
    decision = engine.authorize_order(
        "BTC/USDT",
        "BUY",
        equity=1000.0,
        proposed_notional=50.0,
        current_exposure=0.0,
        current_symbol_exposure=0.0,
        current_open_positions=0,
        max_open_positions=2,
        max_total_exposure_pct=0.35,
        max_symbol_exposure_pct=0.25,
        stop_pct=0.0,
        now=100.0,
    )
    assert decision.authorized is False
    assert decision.reason == "risk engine requires a positive stop"


def test_authorize_order_preserves_global_risk_block():
    engine = RiskEngine({"max_daily_loss_pct": -0.01})
    engine.state.pnl_today_pct = -0.02
    decision = engine.authorize_order(
        "BTC/USDT",
        "BUY",
        equity=1000.0,
        proposed_notional=50.0,
        current_exposure=0.0,
        current_symbol_exposure=0.0,
        current_open_positions=0,
        max_open_positions=2,
        max_total_exposure_pct=0.35,
        max_symbol_exposure_pct=0.25,
        stop_pct=0.01,
        now=100.0,
    )
    assert decision.authorized is False
    assert "daily drawdown" in decision.reason
