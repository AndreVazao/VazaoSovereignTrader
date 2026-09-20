from __future__ import annotations

from PC_ENGINE.core.engine import Position, RuntimeState, SovereignEngine


class FakeExchange:
    name = "fake"

    def __init__(self, balance, open_orders):
        self.balance = balance
        self.open_orders = open_orders

    def fetch_balance(self):
        return self.balance

    def fetch_open_orders(self):
        return self.open_orders


def make_engine(balance, open_orders, positions):
    engine = object.__new__(SovereignEngine)
    engine.mode = "REAL"
    engine.paper = False
    engine.config = {"engine": {"quote_currency": "USDT"}}
    engine.state = RuntimeState(mode="REAL", open_positions=positions)
    engine.exchanges = {"fake": FakeExchange(balance, open_orders)}
    engine.ledger = type("Ledger", (), {"event": lambda self, *args, **kwargs: None})()
    return engine


def test_account_reconciliation_matches_local_positions_and_no_open_orders():
    positions = {"BTC/USDT": Position("fake", "BTC/USDT", 100.0, 0.5, 90.0, 120.0, 1.0)}
    engine = make_engine({"total": {"BTC": 0.5, "USDT": 1000.0}}, [], positions)
    result = engine.reconcile_account_state()
    assert result["ok"] is True
    assert result["status"] == "MATCH"


def test_account_reconciliation_blocks_position_mismatch():
    positions = {"BTC/USDT": Position("fake", "BTC/USDT", 100.0, 0.5, 90.0, 120.0, 1.0)}
    engine = make_engine({"total": {"BTC": 0.2, "USDT": 1000.0}}, [], positions)
    result = engine.reconcile_account_state()
    assert result["ok"] is False
    assert result["status"] == "BLOCKED"
    assert engine.state.status == "SAFE_MODE"


def test_account_reconciliation_blocks_unexpected_assets_and_open_orders():
    engine = make_engine(
        {"total": {"ETH": 1.0, "USDT": 1000.0}},
        [{"id": "open-1", "symbol": "BTC/USDT"}],
        {},
    )
    result = engine.reconcile_account_state()
    assert result["ok"] is False
    assert result["open_orders"] == 1
    assert result["unexpected_assets"][0]["asset"] == "ETH"
