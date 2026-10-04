from __future__ import annotations

from PC_ENGINE.core.engine import RuntimeState, SovereignEngine


class RecoveryExchange:
    name = "fake"

    def __init__(self, open_orders=None, historical=None):
        self.open_orders = open_orders or []
        self.historical = historical
        self.lookups = []

    def fetch_open_orders(self):
        return self.open_orders

    def fetch_order_by_client_order_id(self, client_order_id, symbol):
        self.lookups.append((client_order_id, symbol))
        if self.historical is None:
            raise LookupError("not found")
        return self.historical


def make_engine(exchange, intents):
    engine = object.__new__(SovereignEngine)
    engine.paper = False
    engine.state = RuntimeState(status="SAFE_MODE", mode="REAL")
    engine.state.execution_intents = intents
    engine.state.pending_orders = {}
    engine.exchanges = {"fake": exchange}
    engine._main_exchange = lambda: exchange
    engine._persist_recovery = lambda: None
    engine.log = lambda *args, **kwargs: None
    engine._enter_safe_state = lambda *args, **kwargs: setattr(engine.state, "status", "SAFE_MODE")
    return engine


def test_unresolved_intent_survives_when_order_id_cannot_be_resolved():
    exchange = RecoveryExchange()
    intents = {
        "intent-1": {
            "exchange": "fake", "symbol": "BTC/USDT", "side": "buy",
            "requested_qty": 0.25, "reference_price": 100.0,
            "client_order_id": "vzt-stable-client-id", "created_ts": 1.0,
        }
    }
    engine = make_engine(exchange, intents)

    engine._recover_unresolved_execution_intents()

    assert "intent-1" in engine.state.execution_intents
    assert engine.state.pending_orders == {}
    assert exchange.lookups == [("vzt-stable-client-id", "BTC/USDT")]


def test_intent_recovers_historical_order_by_client_id_without_assuming_fill():
    historical = {
        "id": "exchange-order-7", "symbol": "BTC/USDT", "side": "buy",
        "status": "closed", "amount": 0.25, "filled": 0.25,
        "clientOrderId": "vzt-stable-client-id", "average": 101.0,
    }
    exchange = RecoveryExchange(historical=historical)
    intents = {
        "intent-1": {
            "exchange": "fake", "symbol": "BTC/USDT", "side": "buy",
            "requested_qty": 0.25, "reference_price": 100.0,
            "client_order_id": "vzt-stable-client-id", "created_ts": 1.0,
        }
    }
    engine = make_engine(exchange, intents)

    engine._recover_unresolved_execution_intents()

    assert "intent-1" not in engine.state.execution_intents
    recovered = engine.state.pending_orders["exchange-order-7"]
    assert recovered["known_filled_qty"] == 0.0
    assert recovered["client_order_id"] == "vzt-stable-client-id"



def test_malformed_intent_quantity_is_preserved_and_fails_closed():
    exchange = RecoveryExchange()
    intents = {
        "intent-bad": {
            "exchange": "fake", "symbol": "BTC/USDT", "side": "buy",
            "requested_qty": "not-a-number",
            "client_order_id": "vzt-bad-client-id", "created_ts": 1.0,
        }
    }
    engine = make_engine(exchange, intents)

    engine._recover_unresolved_execution_intents()

    assert "intent-bad" in engine.state.execution_intents
    assert engine.state.pending_orders == {}
    assert engine.state.status == "SAFE_MODE"
    assert exchange.lookups == []


def test_historical_order_identity_mismatch_does_not_consume_intent():
    historical = {
        "id": "wrong-order", "symbol": "ETH/USDT", "side": "sell",
        "status": "closed", "amount": 0.25, "filled": 0.25,
        "clientOrderId": "different-client-id", "average": 101.0,
    }
    exchange = RecoveryExchange(historical=historical)
    intents = {
        "intent-1": {
            "exchange": "fake", "symbol": "BTC/USDT", "side": "buy",
            "requested_qty": 0.25, "reference_price": 100.0,
            "client_order_id": "vzt-stable-client-id", "created_ts": 1.0,
        }
    }
    engine = make_engine(exchange, intents)

    engine._recover_unresolved_execution_intents()

    assert "intent-1" in engine.state.execution_intents
    assert engine.state.pending_orders == {}
    assert engine.state.status == "SAFE_MODE"


def test_recovery_uses_the_intent_recorded_venue_not_main_exchange():
    primary = RecoveryExchange(open_orders=[{
        "id": "wrong-venue-order", "symbol": "BTC/USDT", "side": "buy",
        "amount": 0.25, "clientOrderId": "vzt-stable-client-id",
    }])
    secondary = RecoveryExchange(open_orders=[{
        "id": "right-venue-order", "symbol": "BTC/USDT", "side": "buy",
        "amount": 0.25, "clientOrderId": "vzt-stable-client-id",
    }])
    intents = {
        "intent-venue": {
            "exchange": "secondary", "symbol": "BTC/USDT", "side": "buy",
            "requested_qty": 0.25, "reference_price": 100.0,
            "client_order_id": "vzt-stable-client-id", "created_ts": 1.0,
        }
    }
    engine = make_engine(primary, intents)
    engine.exchanges = {"primary": primary, "secondary": secondary}
    engine._main_exchange = lambda: primary

    engine._recover_unresolved_execution_intents()

    assert "wrong-venue-order" not in engine.state.pending_orders
    assert "right-venue-order" in engine.state.pending_orders
    assert engine.state.pending_orders["right-venue-order"]["venue_id"] == "secondary"
    assert "intent-venue" not in engine.state.execution_intents


def test_recovery_rejects_open_order_with_incomplete_identity_fields():
    exchange = RecoveryExchange(open_orders=[{
        "id": "incomplete-order",
        "clientOrderId": "vzt-stable-client-id",
    }])
    intents = {
        "intent-incomplete": {
            "exchange": "fake", "symbol": "BTC/USDT", "side": "buy",
            "requested_qty": 0.25, "reference_price": 100.0,
            "client_order_id": "vzt-stable-client-id", "created_ts": 1.0,
        }
    }
    engine = make_engine(exchange, intents)

    engine._recover_unresolved_execution_intents()

    assert "intent-incomplete" in engine.state.execution_intents
    assert engine.state.pending_orders == {}
    assert engine.state.status == "SAFE_MODE"
