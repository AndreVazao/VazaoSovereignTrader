from __future__ import annotations

from PC_ENGINE.core.engine import RuntimeState, SovereignEngine


def test_new_execution_intent_recovers_only_matching_client_order_id():
    class Exchange:
        name = "binance"

        def fetch_open_orders(self, symbol=None):
            return [
                {
                    "id": "wrong",
                    "symbol": "BTC/USDT",
                    "side": "buy",
                    "amount": 0.1,
                    "clientOrderId": "other-id",
                },
                {
                    "id": "right",
                    "symbol": "BTC/USDT",
                    "side": "buy",
                    "amount": 0.1,
                    "clientOrderId": "vzt-123-buy",
                },
            ]

    engine = object.__new__(SovereignEngine)
    engine.paper = False
    engine.state = RuntimeState(
        execution_intents={
            "intent-1": {
                "exchange": "binance",
                "symbol": "BTC/USDT",
                "side": "buy",
                "requested_qty": 0.1,
                "reference_price": 100.0,
                "client_order_id": "vzt-123-buy",
                "created_ts": 1.0,
            }
        }
    )
    engine._main_exchange = lambda: Exchange()
    engine._persist_recovery = lambda: None
    engine.log = lambda *args, **kwargs: None

    engine._recover_unresolved_execution_intents()

    assert engine.state.execution_intents == {}
    assert "right" in engine.state.pending_orders
    assert "wrong" not in engine.state.pending_orders
    assert engine.state.pending_orders["right"]["client_order_id"] == "vzt-123-buy"


def test_new_execution_intent_does_not_fallback_to_quantity_matching():
    class Exchange:
        name = "binance"

        def fetch_open_orders(self, symbol=None):
            return [
                {
                    "id": "unrelated",
                    "symbol": "BTC/USDT",
                    "side": "buy",
                    "amount": 0.1,
                    "clientOrderId": "unrelated-id",
                }
            ]

    engine = object.__new__(SovereignEngine)
    engine.paper = False
    engine.state = RuntimeState(
        execution_intents={
            "intent-1": {
                "symbol": "BTC/USDT",
                "side": "buy",
                "requested_qty": 0.1,
                "client_order_id": "vzt-123-buy",
            }
        }
    )
    engine._main_exchange = lambda: Exchange()
    engine._persist_recovery = lambda: None
    engine.log = lambda *args, **kwargs: None

    engine._recover_unresolved_execution_intents()

    assert "intent-1" in engine.state.execution_intents
    assert engine.state.pending_orders == {}
