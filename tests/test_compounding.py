from PC_ENGINE.core.compounding import CompoundingController


def test_profit_is_compounded_into_next_equity_base():
    c = CompoundingController(owner_id="andre", venue="binance")
    assert c.next_trade_equity(current_equity=1.0, realized_pnl=0.10) == 1.10
    assert c.next_trade_equity(current_equity=1.10, realized_pnl=0.11) == 1.21


def test_losses_reduce_next_equity_base():
    c = CompoundingController(owner_id="andre", venue="binance")
    assert c.next_trade_equity(current_equity=100.0, realized_pnl=-2.0) == 98.0


def test_snapshot_preserves_compounding_equity_and_separates_surplus():
    c = CompoundingController(owner_id="andre", venue="binance", reserve_cash_pct=0.20)
    s = c.snapshot(baseline_capital=100.0, equity=110.0, adaptive_risk_multiplier=1.2)
    assert s.reinvestment_equity == 88.0
    assert s.transferable_surplus == 10.0
    assert s.realized_profit == 10.0
    assert s.status == "PROFIT_COMPOUNDING"


def test_recovery_does_not_falsely_report_profit():
    c = CompoundingController(owner_id="andre", venue="binance")
    s = c.snapshot(baseline_capital=100.0, equity=98.0)
    assert s.realized_profit == -2.0
    assert s.transferable_surplus == 0.0
    assert s.status == "RECOVERY"
