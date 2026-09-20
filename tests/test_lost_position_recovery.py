from __future__ import annotations

from PC_ENGINE.core.engine import Position, RuntimeState, SovereignEngine


def test_pending_buy_recreates_position_when_local_position_was_lost():
    class Exchange:
        name = "binance"

        def fetch_order(self, order_id, symbol):
            return {
                "id": order_id,
                "symbol": symbol,
                "side": "buy",
                "status": "closed",
                "filled": 0.25,
                "average": 200.0,
                "fees": [{"cost": 0.05, "currency": "USDT"}],
            }

    engine = object.__new__(SovereignEngine)
    engine.state = RuntimeState(
        pending_orders={
            "order-1": {
                "exchange": "binance",
                "symbol": "BTC/USDT",
                "side": "buy",
                "requested_qty": 0.25,
                "known_filled_qty": 0.0,
                "known_fill_price": 0.0,
                "created_ts": 123.0,
                "stop_pct": 0.02,
                "take_profit_pct": 0.04,
            }
        }
    )
    engine._main_exchange = lambda: Exchange()
    engine._persist_recovery = lambda: None
    engine.log = lambda *args, **kwargs: None

    engine._reconcile_pending_orders()

    position = engine.state.open_positions["BTC/USDT"]
    assert position.qty == 0.25
    assert position.entry == 200.0
    assert position.stop == 196.0
    assert position.take_profit == 208.0
    assert position.entry_fee == 0.05
    assert engine.state.pending_orders == {}


def test_pending_sell_never_creates_position_when_local_position_is_missing():
    class Exchange:
        name = "binance"

        def fetch_order(self, order_id, symbol):
            return {
                "id": order_id,
                "symbol": symbol,
                "side": "sell",
                "status": "closed",
                "filled": 0.1,
                "average": 210.0,
                "fee": {"cost": 0.01},
            }

    engine = object.__new__(SovereignEngine)
    engine.state = RuntimeState(
        pending_orders={
            "order-2": {
                "exchange": "binance",
                "symbol": "BTC/USDT",
                "side": "sell",
                "requested_qty": 0.1,
                "known_filled_qty": 0.0,
            }
        }
    )
    engine._main_exchange = lambda: Exchange()
    engine._persist_recovery = lambda: None
    engine.log = lambda *args, **kwargs: None

    engine._reconcile_pending_orders()

    assert engine.state.open_positions == {}
    assert engine.state.status == "SAFE_MODE"
    assert "order-2" in engine.state.pending_orders
