from __future__ import annotations

import threading

from PC_ENGINE.core.engine import Position, RuntimeState, SovereignEngine


class FakeExchange:
    name = "fake"

    def __init__(self, order):
        self.order = order

    def fetch_order(self, order_id: str, symbol: str):
        return self.order


class FakeRecovery:
    def save_positions(
        self,
        positions,
        pending_orders=None,
        order_guards=None,
        execution_intents=None,
        financial_account=None,
        risk_state=None,
    ):
        self.saved = (
            positions,
            pending_orders,
            order_guards,
            execution_intents,
            financial_account,
            risk_state,
        )


class FakeLedger:
    def __init__(self):
        self.events = []
        self.trades = []

    def event(self, message, data):
        self.events.append((message, data))

    def trade(self, data):
        self.trades.append(data)


class FakeRisk:
    class State:
        drawdown_pct = 0.0

    state = State()

    def record_trade_result(self, symbol, pnl_pct):
        pass

    def snapshot_state(self):
        return {}


class FakeChampion:
    def record(self, *args, **kwargs):
        pass


def make_engine(order, position, pending):
    engine = object.__new__(SovereignEngine)
    engine.lock = threading.RLock()
    engine.state = RuntimeState(status="SAFE_MODE", mode="REAL")
    engine.state.open_positions[position.symbol] = position
    engine.state.pending_orders = pending
    engine.exchanges = {"fake": FakeExchange(order)}
    engine.recovery = FakeRecovery()
    engine.ledger = FakeLedger()
    engine.risk = FakeRisk()
    engine.champion = FakeChampion()
    engine.order_manager = type("OrderManagerStub", (), {"export_order_guards": lambda self: {}})()
    engine.paper = True
    return engine


def test_reconcile_pending_buy_applies_only_unseen_fill_delta():
    position = Position("fake", "BTC/USDT", 100.0, 0.2, 90.0, 120.0, 1.0)
    engine = make_engine(
        {"id": "buy-1", "status": "closed", "filled": 0.5, "average": 102.0, "fee": {"cost": 0.01, "currency": "USDT"}},
        position,
        {"buy-1": {
            "symbol": "BTC/USDT",
            "side": "buy",
            "requested_qty": 0.5,
            "known_filled_qty": 0.2,
            "known_fill_price": 100.0,
            "known_quote_notional": 20.0,
            "known_fee": 0.0,
        }},
    )

    engine._reconcile_pending_orders()

    assert engine.state.open_positions["BTC/USDT"].qty == 0.5
    assert engine.state.pending_orders == {}


def test_reconcile_pending_sell_reduces_position_by_unseen_fill_delta():
    position = Position("fake", "BTC/USDT", 100.0, 0.8, 90.0, 120.0, 1.0, entry_fee=0.08)
    engine = make_engine(
        {"id": "sell-1", "status": "closed", "filled": 0.5, "average": 110.0, "fee": {"cost": 0.02, "currency": "USDT"}},
        position,
        {"sell-1": {
            "symbol": "BTC/USDT",
            "side": "sell",
            "requested_qty": 0.5,
            "known_filled_qty": 0.2,
            "known_fill_price": 109.0,
            "known_quote_notional": 21.8,
            "known_fee": 0.0,
        }},
    )

    engine._reconcile_pending_orders()

    assert engine.state.open_positions["BTC/USDT"].qty == 0.5
    assert engine.state.pending_orders == {}
    assert len(engine.ledger.trades) == 1


def test_reconcile_unknown_status_keeps_safe_mode_and_pending_order():
    position = Position("fake", "BTC/USDT", 100.0, 0.2, 90.0, 120.0, 1.0)
    engine = make_engine(
        {"id": "buy-unknown", "status": "mystery", "filled": 0.2, "average": 100.0},
        position,
        {"buy-unknown": {"symbol": "BTC/USDT", "side": "buy", "known_filled_qty": 0.2}},
    )
    engine._reconcile_pending_orders()
    assert engine.state.status == "SAFE_MODE"
    assert "buy-unknown" in engine.state.pending_orders


def test_reconcile_open_order_keeps_safe_mode_and_pending_order():
    position = Position("fake", "BTC/USDT", 100.0, 0.2, 90.0, 120.0, 1.0)
    engine = make_engine(
        {"id": "buy-open", "status": "open", "filled": 0.2, "average": 100.0},
        position,
        {"buy-open": {"symbol": "BTC/USDT", "side": "buy", "known_filled_qty": 0.2}},
    )
    engine._reconcile_pending_orders()
    assert engine.state.status == "SAFE_MODE"
    assert "buy-open" in engine.state.pending_orders


def test_terminal_order_missing_filled_quantity_is_not_discarded():
    position = Position("fake", "BTC/USDT", 100.0, 0.2, 90.0, 120.0, 1.0)
    engine = make_engine(
        {"id": "buy-no-filled", "status": "closed", "average": 100.0},
        position,
        {"buy-no-filled": {
            "symbol": "BTC/USDT",
            "side": "buy",
            "requested_qty": 0.5,
            "known_filled_qty": 0.0,
        }},
    )

    engine._reconcile_pending_orders()

    assert engine.state.status == "SAFE_MODE"
    assert "buy-no-filled" in engine.state.pending_orders
    assert engine.state.open_positions["BTC/USDT"].qty == 0.2



def test_nonzero_fee_without_currency_fails_closed():
    engine = object.__new__(SovereignEngine)
    import pytest

    with pytest.raises(ValueError, match="currency is unknown"):
        engine._extract_cumulative_quote_fee({"fee": 0.01}, "BTC/USDT")


def test_fee_in_non_quote_currency_fails_closed():
    engine = object.__new__(SovereignEngine)
    import pytest

    with pytest.raises(ValueError, match="not quote-denominated"):
        engine._extract_cumulative_quote_fee(
            {"fee": {"cost": 0.01, "currency": "BNB"}}, "BTC/USDT"
        )


def test_nonfinite_or_negative_fee_fails_closed():
    engine = object.__new__(SovereignEngine)
    import pytest

    for fee in (float("nan"), float("inf"), -0.01):
        with pytest.raises(ValueError):
            engine._extract_cumulative_quote_fee({"fee": fee}, "BTC/USDT")


def test_quote_fee_is_accepted_only_with_matching_currency():
    engine = object.__new__(SovereignEngine)

    assert engine._extract_cumulative_quote_fee(
        {"fee": {"cost": 0.01, "currency": "usdt"}}, "BTC/USDT"
    ) == 0.01


def test_ambiguous_fee_keeps_order_pending_and_enters_safe_mode():
    position = Position("fake", "BTC/USDT", 100.0, 0.2, 90.0, 120.0, 1.0)
    engine = make_engine(
        {
            "id": "buy-ambiguous-fee",
            "status": "closed",
            "filled": 0.5,
            "average": 100.0,
            "fee": 0.01,
        },
        position,
        {
            "buy-ambiguous-fee": {
                "symbol": "BTC/USDT",
                "side": "buy",
                "requested_qty": 0.5,
                "known_filled_qty": 0.0,
                "known_fill_price": 100.0,
            }
        },
    )

    engine._reconcile_pending_orders()

    assert engine.state.status == "SAFE_MODE"
    assert "buy-ambiguous-fee" in engine.state.pending_orders
    assert engine.state.open_positions["BTC/USDT"].qty == 0.2
    assert not engine.ledger.trades
