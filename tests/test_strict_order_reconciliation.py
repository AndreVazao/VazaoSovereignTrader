from __future__ import annotations

from PC_ENGINE.core.engine import RuntimeState, SovereignEngine


def _engine(exchange):
    engine = object.__new__(SovereignEngine)
    engine.state = RuntimeState(
        pending_orders={
            "order-strict": {
                "exchange": "binance",
                "symbol": "BTC/USDT",
                "side": "buy",
                "requested_qty": 1.0,
                "known_filled_qty": 0.0,
                "known_fee": 0.0,
                "known_fill_price": 100.0,
                "client_order_id": "vzt-strict",
                "created_ts": 123.0,
                "stop_pct": 0.02,
                "take_profit_pct": 0.04,
            }
        }
    )
    engine._main_exchange = lambda: exchange
    engine._persist_recovery = lambda: None
    engine.log = lambda *args, **kwargs: None
    return engine


def test_reconciliation_blocks_exchange_overfill():
    class Exchange:
        name = "binance"

        def fetch_order(self, order_id, symbol):
            return {
                "id": order_id, "symbol": symbol, "side": "buy",
                "status": "closed", "filled": 1.1, "average": 100.0,
                "clientOrderId": "vzt-strict",
            }

    engine = _engine(Exchange())
    engine._reconcile_pending_orders()
    assert engine.state.status == "SAFE_MODE"
    assert "order-strict" in engine.state.pending_orders
    assert engine.state.open_positions == {}


def test_reconciliation_blocks_fill_regression():
    class Exchange:
        name = "binance"

        def fetch_order(self, order_id, symbol):
            return {
                "id": order_id, "symbol": symbol, "side": "buy",
                "status": "closed", "filled": 0.4, "average": 100.0,
                "clientOrderId": "vzt-strict",
            }

    engine = _engine(Exchange())
    engine.state.pending_orders["order-strict"]["known_filled_qty"] = 0.5
    engine._reconcile_pending_orders()
    assert engine.state.status == "SAFE_MODE"
    assert "order-strict" in engine.state.pending_orders
    assert engine.state.open_positions == {}


def test_reconciliation_blocks_returned_side_mismatch():
    class Exchange:
        name = "binance"

        def fetch_order(self, order_id, symbol):
            return {
                "id": order_id, "symbol": symbol, "side": "sell",
                "status": "closed", "filled": 1.0, "average": 100.0,
                "clientOrderId": "vzt-strict",
            }

    engine = _engine(Exchange())
    engine._reconcile_pending_orders()
    assert engine.state.status == "SAFE_MODE"
    assert "order-strict" in engine.state.pending_orders
    assert engine.state.open_positions == {}


def test_reconciliation_blocks_fee_regression():
    class Exchange:
        name = "binance"

        def fetch_order(self, order_id, symbol):
            return {
                "id": order_id, "symbol": symbol, "side": "buy",
                "status": "closed", "filled": 1.0, "average": 100.0,
                "clientOrderId": "vzt-strict",
                "fee": {"cost": 0.1, "currency": "USDT"},
            }

    engine = _engine(Exchange())
    engine.state.pending_orders["order-strict"]["known_fee"] = 0.2
    engine._reconcile_pending_orders()
    assert engine.state.status == "SAFE_MODE"
    assert "order-strict" in engine.state.pending_orders
    assert engine.state.open_positions == {}
