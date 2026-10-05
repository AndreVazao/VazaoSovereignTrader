from __future__ import annotations

from types import SimpleNamespace

from PC_ENGINE.core.order_manager import OrderManager


class RulesStub:
    def validate_order(self, exchange, symbol, qty, price):
        return True, "", float(qty)


class PaperStub:
    def fill(self, symbol, side, qty, price, spread_pct):
        return SimpleNamespace(fill_price=price, fee=0.0)


class ExchangeStub:
    name = "TEST"
    
    def __init__(self):
        self.calls = 0

    def market_buy(self, symbol, qty):
        self.calls += 1
        return {
            "id": "order-1",
            "status": "closed",
            "filled": qty,
            "average": 100.0,
            "fee": {"cost": 0.0, "currency": "USDT"},
        }

    def market_sell(self, symbol, qty):
        self.calls += 1
        return {
            "id": "order-2",
            "status": "closed",
            "filled": qty,
            "average": 101.0,
            "fee": {"cost": 0.0, "currency": "USDT"},
        }


def test_real_order_requires_authorizer_before_adapter_call():
    exchange = ExchangeStub()
    manager = OrderManager(RulesStub(), PaperStub())

    result = manager.buy(exchange, "BTC/USDT", 0.1, 100.0, paper=False, client_order_id="client-1")

    assert result.status == "REJECTED"
    assert "authorization required" in result.reason
    assert exchange.calls == 0


def test_real_order_authorizer_must_explicitly_return_true():
    exchange = ExchangeStub()
    manager = OrderManager(
        RulesStub(),
        PaperStub(),
        execution_authorizer=lambda *args: False,
    )

    result = manager.buy(exchange, "BTC/USDT", 0.1, 100.0, paper=False, client_order_id="client-1")

    assert result.status == "REJECTED"
    assert "authorization denied" in result.reason
    assert exchange.calls == 0


def test_real_order_authorizer_runs_immediately_before_adapter():
    exchange = ExchangeStub()
    seen = []

    def authorize(exchange_name, symbol, side, quantity, client_order_id):
        seen.append((exchange_name, symbol, side, quantity, client_order_id, exchange.calls))
        return True

    manager = OrderManager(RulesStub(), PaperStub(), execution_authorizer=authorize)

    result = manager.sell(exchange, "BTC/USDT", 0.1, 100.0, paper=False, client_order_id="client-2")

    assert result.status == "FILLED"
    assert exchange.calls == 1
    assert seen == [("TEST", "BTC/USDT", "sell", 0.1, "client-2", 0)]
