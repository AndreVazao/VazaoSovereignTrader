from __future__ import annotations

from PC_ENGINE.core.engine import RuntimeState, SovereignEngine


def _engine(exchange):
    engine = object.__new__(SovereignEngine)
    engine.config = {"reconciliation": {"financial_relative_tolerance": 0.002}}
    engine.state = RuntimeState()
    engine._main_exchange = lambda: exchange
    engine._persist_recovery = lambda: None
    engine.log = lambda *args, **kwargs: None
    return engine


def test_financial_invariant_accepts_consistent_cost():
    engine = _engine(None)
    result = engine._validate_order_financial_invariant(
        {"cost": 100.0, "fee": {"cost": 0.1}},
        "BTC/USDT",
        1.0,
        100.0,
    )
    assert result["ok"] is True


def test_financial_invariant_blocks_cost_quantity_price_mismatch():
    engine = _engine(None)
    result = engine._validate_order_financial_invariant(
        {"cost": 130.0},
        "BTC/USDT",
        1.0,
        100.0,
    )
    assert result["ok"] is False
    assert result["reason"] == "order_cost_price_quantity_mismatch"


def test_financial_invariant_blocks_negative_fee():
    engine = _engine(None)
    result = engine._validate_order_financial_invariant(
        {"cost": 100.0, "fee": {"cost": -0.1}},
        "BTC/USDT",
        1.0,
        100.0,
    )
    assert result["ok"] is False
    assert result["reason"] == "negative_fee"
