from types import SimpleNamespace

import pytest

from PC_ENGINE.core.engine import SovereignEngine


class PendingOrderManager:
    def __init__(self, result):
        self.result = result

    def buy(self, *args, **kwargs):
        return self.result

    def sell(self, *args, **kwargs):
        return self.result


def make_engine(result, *, position=None):
    state = SimpleNamespace(
        execution_intents={},
        pending_orders={},
        open_positions={} if position is None else {position.symbol: position},
    )
    engine = SimpleNamespace(
        paper=True,
        state=state,
        order_manager=PendingOrderManager(result),
        _persist_recovery=lambda: None,
        _enter_safe_state=lambda *args, **kwargs: None,
        log=lambda *args, **kwargs: None,
    )
    return engine


def pending_result():
    return SimpleNamespace(
        status="PENDING_OR_PARTIAL",
        qty=0.25,
        requested_qty=1.0,
        order_id="order-123",
        price=100.0,
        fee=0.1,
        ok=True,
        reason="partial fill awaiting reconciliation",
    )


def test_pending_partial_buy_does_not_create_position_before_reconciliation():
    engine = make_engine(pending_result())
    exchange = SimpleNamespace(name="demo")

    SovereignEngine._open_position(
        engine, exchange, "BTC/USDT", 100.0, 1.0, 0.02, 0.04, "test"
    )

    assert engine.state.open_positions == {}
    pending = engine.state.pending_orders["order-123"]
    assert pending["known_filled_qty"] == 0.0
    assert "intent-" not in str(engine.state.execution_intents)


def test_pending_partial_sell_does_not_reduce_position_before_reconciliation():
    position = SimpleNamespace(
        exchange="demo",
        symbol="BTC/USDT",
        qty=1.0,
        entry=90.0,
        stop=85.0,
        take_profit=110.0,
        entry_fee=0.2,
    )
    engine = make_engine(pending_result(), position=position)
    exchange = SimpleNamespace(name="demo")

    SovereignEngine._close_position(engine, exchange, position, 100.0, "test")

    assert engine.state.open_positions["BTC/USDT"].qty == 1.0
    pending = engine.state.pending_orders["order-123"]
    assert pending["known_filled_qty"] == 0.0
