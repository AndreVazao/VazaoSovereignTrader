from __future__ import annotations

from PC_ENGINE.core.engine import RuntimeState, SovereignEngine
from PC_ENGINE.execution.browser_execution_ledger import BrowserExecutionLedger


class FakeExchange:
    name = "binance"

    def __init__(self, raw=None, client_raw=None):
        self.raw = raw
        self.client_raw = client_raw
        self.fetch_order_calls = 0
        self.client_lookup_calls = 0

    def fetch_order(self, order_id, symbol):
        self.fetch_order_calls += 1
        if isinstance(self.raw, Exception):
            raise self.raw
        return dict(self.raw or {})

    def fetch_order_by_client_order_id(self, client_order_id, symbol):
        self.client_lookup_calls += 1
        if isinstance(self.client_raw, Exception):
            raise self.client_raw
        return dict(self.client_raw or {})


def _engine(exchange):
    engine = object.__new__(SovereignEngine)
    engine.state = RuntimeState(status="SAFE_MODE", mode="REAL")
    engine.exchanges = {"binance": exchange}
    engine.paper = False
    engine.mode = "REAL"
    engine.config = {"reconciliation": {"financial_relative_tolerance": 0.002}}
    engine.lock = __import__("threading").RLock()
    engine.logs = []
    engine._enter_safe_state = lambda *args, **kwargs: setattr(engine.state, "status", "SAFE_MODE")
    engine.log = lambda message, data=None: engine.state.logs.append(message if data is None else f"{message}: {data}")
    engine._persist_recovery = lambda: None
    engine._record_financial_fill = lambda *args, **kwargs: None
    return engine


def test_browser_pending_uses_recorded_venue():
    exchange = FakeExchange({
        "id": "order-1",
        "symbol": "BTC/USDT",
        "side": "buy",
        "status": "closed",
        "filled": 1.0,
        "average": 100.0,
        "cost": 100.0,
        "fee": {"currency": "USDT", "cost": 0.1},
        "clientOrderId": "browser-key",
    })
    engine = _engine(exchange)
    engine.state.pending_orders = {
        "order-1": {
            "venue_id": "binance",
            "symbol": "BTC/USDT",
            "side": "buy",
            "requested_qty": 1.0,
            "known_filled_qty": 0.0,
            "known_fee": 0.0,
            "known_quote_notional": 0.0,
            "known_fill_price": 0.0,
            "client_order_id": "browser-key",
            "browser_execution": True,
            "stop_pct": 0.02,
            "take_profit_pct": 0.04,
        }
    }
    engine._reconcile_pending_orders()
    assert exchange.fetch_order_calls == 1
    assert "order-1" not in engine.state.pending_orders


def test_browser_pending_falls_back_to_client_order_id():
    exchange = FakeExchange(
        raw=LookupError("external id unavailable"),
        client_raw={
            "id": "exchange-order-9",
            "symbol": "ETH/USDT",
            "side": "buy",
            "status": "closed",
            "filled": 2.0,
            "average": 50.0,
            "cost": 100.0,
            "fee": {"currency": "USDT", "cost": 0.1},
            "clientOrderId": "browser-key-9",
        },
    )
    engine = _engine(exchange)
    engine.state.pending_orders = {
        "browser-external-9": {
            "venue_id": "binance",
            "symbol": "ETH/USDT",
            "side": "buy",
            "requested_qty": 2.0,
            "known_filled_qty": 0.0,
            "known_fee": 0.0,
            "known_quote_notional": 0.0,
            "known_fill_price": 0.0,
            "client_order_id": "browser-key-9",
            "browser_execution": True,
        }
    }
    engine._reconcile_pending_orders()
    assert exchange.fetch_order_calls == 1
    assert exchange.client_lookup_calls == 1
    assert "browser-external-9" not in engine.state.pending_orders
    assert any("BROWSER_PENDING_ORDER_RESOLVED_BY_CLIENT_ID" in log for log in engine.state.logs)


def test_non_browser_pending_does_not_use_client_id_fallback():
    exchange = FakeExchange(
        raw=LookupError("external id unavailable"),
        client_raw={"id": "should-not-be-used"},
    )
    engine = _engine(exchange)
    engine.state.pending_orders = {
        "order-legacy": {
            "venue_id": "binance",
            "symbol": "BTC/USDT",
            "side": "buy",
            "requested_qty": 1.0,
            "known_filled_qty": 0.0,
            "known_fee": 0.0,
            "known_quote_notional": 0.0,
            "known_fill_price": 0.0,
            "client_order_id": "legacy-key",
            "browser_execution": False,
        }
    }
    engine._reconcile_pending_orders()
    assert exchange.client_lookup_calls == 0
    assert "order-legacy" in engine.state.pending_orders
