from __future__ import annotations

from PC_ENGINE.core.engine import RuntimeState, SovereignEngine


def _engine():
    engine = object.__new__(SovereignEngine)
    engine.config = {"reconciliation": {"financial_relative_tolerance": 0.002}}
    engine.state = RuntimeState()
    engine.paper = False
    return engine


def test_financial_invariant_accepts_consistent_cost():
    result = _engine()._validate_order_financial_invariant(
        {"cost": 100.0, "fee": {"cost": 0.1}}, "BTC/USDT", 1.0, 100.0
    )
    assert result["ok"] is True


def test_financial_invariant_blocks_cost_quantity_price_mismatch():
    result = _engine()._validate_order_financial_invariant(
        {"cost": 130.0}, "BTC/USDT", 1.0, 100.0
    )
    assert result["ok"] is False
    assert result["reason"] == "order_cost_price_quantity_mismatch"


def test_financial_invariant_blocks_negative_fee():
    result = _engine()._validate_order_financial_invariant(
        {"cost": 100.0, "fee": {"cost": -0.1}}, "BTC/USDT", 1.0, 100.0
    )
    assert result["ok"] is False
    assert result["reason"] == "negative_fee"


def test_financial_invariant_uses_incremental_notional_for_partial_fill():
    first_cost = 0.4 * 100.0
    final_cost = 1.0 * 102.0
    delta_qty = 1.0 - 0.4
    delta_notional = final_cost - first_cost
    assert abs(delta_notional / delta_qty - (62.0 / 0.6)) < 1e-12
