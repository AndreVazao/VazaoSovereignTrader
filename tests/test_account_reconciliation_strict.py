from __future__ import annotations

from PC_ENGINE.core.engine import Position, RuntimeState, SovereignEngine


class Exchange:
    name = "binance"

    def __init__(self, total, open_orders=None):
        self.total = total
        self.open_orders = open_orders or []

    def fetch_balance(self):
        return {"total": self.total}

    def fetch_open_orders(self, symbol=None):
        return self.open_orders


def make_engine(exchange, positions):
    engine = object.__new__(SovereignEngine)
    engine.paper = False
    engine.config = {"engine": {"quote_currency": "USDT"}, "reconciliation": {"dust_tolerance": 1e-8, "relative_tolerance": 0.001, "financial_relative_tolerance": 0.002}}
    engine.state = RuntimeState(open_positions=positions)
    engine._main_exchange = lambda: exchange
    engine.log = lambda *args, **kwargs: None
    return engine


def test_reconciliation_aggregates_same_base_asset():
    positions = {
        "BTC/USDT": Position("binance", "BTC/USDT", 100, 0.2, 98, 104, 1),
        "BTC/USDC": Position("binance", "BTC/USDC", 110, 0.3, 108, 114, 2),
    }
    engine = make_engine(Exchange({"BTC": 0.5, "USDT": 1000}), positions)
    result = engine.reconcile_account_state()
    assert result["ok"] is True
    assert result["expected_assets"]["BTC"] == 0.5


def test_reconciliation_blocks_non_dust_unexpected_asset():
    positions = {}
    engine = make_engine(Exchange({"ETH": 0.01, "USDT": 1000}), positions)
    result = engine.reconcile_account_state()
    assert result["ok"] is False
    assert result["unexpected_assets"][0]["asset"] == "ETH"


def test_reconciliation_ignores_configured_dust():
    engine = make_engine(Exchange({"ETH": 1e-10, "USDT": 1000}), {})
    result = engine.reconcile_account_state()
    assert result["ok"] is True


def test_reconciliation_blocks_open_orders_even_when_balances_match():
    engine = make_engine(Exchange({"BTC": 0.5, "USDT": 1000}, [{"id": "o1"}]), {
        "BTC/USDT": Position("binance", "BTC/USDT", 100, 0.5, 98, 104, 1)
    })
    result = engine.reconcile_account_state()
    assert result["ok"] is False
    assert result["open_order_ids"] == ["o1"]


def test_financial_quote_invariant_blocks_unexplained_balance_change():
    engine = make_engine(Exchange({"USDT": 1000}), {})
    assert engine.reconcile_account_state()["ok"] is True
    engine._main_exchange = lambda: Exchange({"USDT": 900})
    result = engine.reconcile_account_state()
    assert result["ok"] is False
    assert result["quote_mismatch"] is True


def test_financial_quote_invariant_accepts_reconciled_quote_flow():
    engine = make_engine(Exchange({"USDT": 1000}), {})
    assert engine.reconcile_account_state()["ok"] is True
    engine.state.financial_account["quote_flow"] = -100.0
    engine._main_exchange = lambda: Exchange({"USDT": 900})
    result = engine.reconcile_account_state()
    assert result["ok"] is True
    assert result["expected_quote"] == 900.0


def test_reconciliation_blocks_base_asset_flow_mismatch_across_symbols():
    positions = {
        "BTC/USDT": Position("binance", "BTC/USDT", 100, 0.2, 98, 104, 1),
        "BTC/USDC": Position("binance", "BTC/USDC", 110, 0.3, 108, 114, 2),
    }
    engine = make_engine(Exchange({"BTC": 0.5, "USDT": 1000}), positions)
    assert engine.reconcile_account_state()["ok"] is True
    engine.state.financial_account["base_flow"] = {"BTC": 0.1}
    result = engine.reconcile_account_state()
    assert result["ok"] is False
    assert result["base_flow_mismatches"][0]["asset"] == "BTC"


def test_reconciliation_accepts_base_asset_flow_across_multiple_symbols():
    positions = {
        "BTC/USDT": Position("binance", "BTC/USDT", 100, 0.2, 98, 104, 1),
        "BTC/USDC": Position("binance", "BTC/USDC", 110, 0.3, 108, 114, 2),
    }
    engine = make_engine(Exchange({"BTC": 0.5, "USDT": 1000}), positions)
    assert engine.reconcile_account_state()["ok"] is True
    engine.state.financial_account["base_flow"] = {"BTC": 0.1}
    engine.state.financial_account["quote_flow"] = -100.0
    engine.state.open_positions["BTC/USDT"].qty = 0.3
    engine.state.open_positions["BTC/USDC"].qty = 0.3
    engine._main_exchange = lambda: Exchange({"BTC": 0.6, "USDT": 900})
    result = engine.reconcile_account_state()
    assert result["ok"] is True
    assert result["expected_assets"]["BTC"] == 0.6
