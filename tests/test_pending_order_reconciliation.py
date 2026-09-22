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
    def save_positions(self, positions, pending_orders=None, order_guards=None, execution_intents=None, financial_account=None):
        self.saved = (positions, pending_orders, order_guards, execution_intents)


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
    return engine


def test_reconcile_pending_buy_applies_only_unseen_fill_delta():
    position = Position("fake", "BTC/USDT", 100.0, 0.2, 90.0, 120.0, 1.0)
    engine = make_engine(
        {"id": "buy-1", "status": "closed", "filled": 0.5, "average": 102.0, "fee": 0.01},
        position,
        {"buy-1": {
            "symbol": "BTC/USDT",
            "side": "buy",
            "known_filled_qty": 0.2,
            "known_fill_price": 100.0,
        }},
    )

    engine._reconcile_pending_orders()

    assert engine.state.open_positions["BTC/USDT"].qty == 0.5
    assert engine.state.pending_orders == {}


def test_reconcile_pending_sell_reduces_position_by_unseen_fill_delta():
    position = Position("fake", "BTC/USDT", 100.0, 0.8, 90.0, 120.0, 1.0, entry_fee=0.08)
    engine = make_engine(
        {"id": "sell-1", "status": "closed", "filled": 0.5, "average": 110.0, "fee": 0.02},
        position,
        {"sell-1": {
            "symbol": "BTC/USDT",
            "side": "sell",
            "known_filled_qty": 0.2,
            "known_fill_price": 109.0,
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
