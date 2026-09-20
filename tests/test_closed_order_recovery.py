from __future__ import annotations

from PC_ENGINE.core.engine import RuntimeState, SovereignEngine


def test_execution_intent_recovers_historical_closed_order_by_exact_client_id():
    class Exchange:
        name = "binance"

        def fetch_open_orders(self, symbol=None):
            return []

        def fetch_order_by_client_order_id(self, client_order_id, symbol):
            assert client_order_id == "vzt-closed-buy"
            assert symbol == "BTC/USDT"
            return {
                "id": "closed-123",
                "symbol": "BTC/USDT",
                "side": "buy",
                "status": "closed",
                "filled": 0.1,
                "average": 100.0,
                "clientOrderId": client_order_id,
            }

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
                "client_order_id": "vzt-closed-buy",
                "created_ts": 1.0,
            }
        }
    )
    engine._main_exchange = lambda: Exchange()
    engine._persist_recovery = lambda: None
    engine.log = lambda *args, **kwargs: None

    engine._recover_unresolved_execution_intents()

    assert engine.state.execution_intents == {}
    assert engine.state.pending_orders["closed-123"]["client_order_id"] == "vzt-closed-buy"
    assert engine.state.pending_orders["closed-123"]["known_filled_qty"] == 0.0


def test_execution_intent_stays_unresolved_when_historical_identity_is_unsupported():
    class Exchange:
        name = "binance"

        def fetch_open_orders(self, symbol=None):
            return []

        def fetch_order_by_client_order_id(self, client_order_id, symbol):
            raise NotImplementedError("unsupported")

    engine = object.__new__(SovereignEngine)
    engine.paper = False
    engine.state = RuntimeState(
        execution_intents={
            "intent-1": {
                "symbol": "BTC/USDT",
                "side": "buy",
                "requested_qty": 0.1,
                "client_order_id": "vzt-missing",
            }
        }
    )
    engine._main_exchange = lambda: Exchange()
    engine._persist_recovery = lambda: None
    engine.log = lambda *args, **kwargs: None

    engine._recover_unresolved_execution_intents()

    assert "intent-1" in engine.state.execution_intents
    assert engine.state.pending_orders == {}
