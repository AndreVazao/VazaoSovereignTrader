from __future__ import annotations

from PC_ENGINE.core.engine import Position, RuntimeState, SovereignEngine


def test_terminal_reconciliation_persists_applied_fill_marker_before_removing_pending():
    class Exchange:
        name = "binance"

        def fetch_order(self, order_id, symbol):
            return {
                "id": order_id,
                "symbol": symbol,
                "side": "buy",
                "status": "closed",
                "filled": 1.0,
                "average": 100.0,
                "clientOrderId": "vzt-1",
                "fees": [{"cost": 1.0, "currency": "USDT"}],
            }

    engine = object.__new__(SovereignEngine)
    engine.state = RuntimeState(
        pending_orders={
            "order-1": {
                "exchange": "binance",
                "symbol": "BTC/USDT",
                "side": "buy",
                "requested_qty": 1.0,
                "known_filled_qty": 0.0,
                "known_fee": 0.0,
                "known_fill_price": 100.0,
                "client_order_id": "vzt-1",
                "created_ts": 123.0,
                "stop_pct": 0.02,
                "take_profit_pct": 0.04,
            }
        }
    )
    engine._main_exchange = lambda: Exchange()
    snapshots = []
    engine._persist_recovery = lambda: snapshots.append(
        (dict(engine.state.pending_orders), dict(engine.state.open_positions))
    )
    engine.log = lambda *args, **kwargs: None

    engine._reconcile_pending_orders()

    assert engine.state.open_positions["BTC/USDT"].qty == 1.0
    assert engine.state.open_positions["BTC/USDT"].entry_fee == 1.0
    assert engine.state.pending_orders == {}
    assert snapshots[0][0]["order-1"]["known_filled_qty"] == 1.0
    assert snapshots[0][0]["order-1"]["known_fee"] == 1.0


def test_reconciliation_blocks_client_order_identity_mismatch():
    class Exchange:
        name = "binance"

        def fetch_order(self, order_id, symbol):
            return {
                "id": order_id,
                "symbol": symbol,
                "side": "buy",
                "status": "closed",
                "filled": 1.0,
                "average": 100.0,
                "clientOrderId": "vzt-wrong",
                "fee": {"cost": 1.0, "currency": "USDT"},
            }

    engine = object.__new__(SovereignEngine)
    engine.state = RuntimeState(
        pending_orders={
            "order-2": {
                "exchange": "binance",
                "symbol": "BTC/USDT",
                "side": "buy",
                "requested_qty": 1.0,
                "known_filled_qty": 0.0,
                "known_fee": 0.0,
                "client_order_id": "vzt-right",
                "stop_pct": 0.02,
                "take_profit_pct": 0.04,
            }
        }
    )
    engine._main_exchange = lambda: Exchange()
    engine._persist_recovery = lambda: None
    engine.log = lambda *args, **kwargs: None

    engine._reconcile_pending_orders()

    assert engine.state.status == "SAFE_MODE"
    assert "order-2" in engine.state.pending_orders
    assert engine.state.open_positions == {}


def test_reconciliation_rejects_base_asset_fee_currency():
    class Exchange:
        name = "binance"

        def fetch_order(self, order_id, symbol):
            return {
                "id": order_id,
                "symbol": symbol,
                "side": "buy",
                "status": "closed",
                "filled": 1.0,
                "average": 100.0,
                "clientOrderId": "vzt-base-fee",
                "fees": [{"cost": 0.001, "currency": "BTC"}],
            }

    engine = object.__new__(SovereignEngine)
    engine.state = RuntimeState(
        pending_orders={
            "order-3": {
                "exchange": "binance",
                "symbol": "BTC/USDT",
                "side": "buy",
                "requested_qty": 1.0,
                "known_filled_qty": 0.0,
                "known_fee": 0.0,
                "client_order_id": "vzt-base-fee",
                "stop_pct": 0.02,
                "take_profit_pct": 0.04,
            }
        }
    )
    engine._main_exchange = lambda: Exchange()
    engine._persist_recovery = lambda: None
    engine.log = lambda *args, **kwargs: None

    engine._reconcile_pending_orders()

    assert engine.state.status == "SAFE_MODE"
    assert "order-3" in engine.state.pending_orders
    assert engine.state.open_positions == {}
