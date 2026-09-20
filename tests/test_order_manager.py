from __future__ import annotations

from PC_ENGINE.core.exchange_rules import ExchangeRulesEngine
from PC_ENGINE.core.order_manager import OrderManager
from PC_ENGINE.core.paper_broker import PaperBroker


class FakeExchange:
    name = "fake"


def test_failed_order_can_retry():
    rules = ExchangeRulesEngine()
    broker = PaperBroker(fee_pct=0.001, slippage_pct=0.0, reject_probability=1.0)
    manager = OrderManager(rules, broker)
    exchange = FakeExchange()

    first = manager.buy(exchange, "BTC/USDT", 0.01, 50000.0, paper=True)
    second = manager.buy(exchange, "BTC/USDT", 0.01, 50000.0, paper=True)

    assert not first.ok
    assert not second.ok
    assert "rejected" in first.reason


def test_successful_order_is_temporarily_deduplicated():
    rules = ExchangeRulesEngine()
    broker = PaperBroker(fee_pct=0.001, slippage_pct=0.0, reject_probability=0.0)
    manager = OrderManager(rules, broker, duplicate_window_seconds=60)
    exchange = FakeExchange()

    first = manager.buy(exchange, "BTC/USDT", 0.01, 50000.0, paper=True)
    second = manager.buy(exchange, "BTC/USDT", 0.01, 50000.0, paper=True)

    assert first.ok
    assert not second.ok
    assert second.reason == "duplicate blocked"

class FakeLiveExchange(FakeExchange):
    def market_buy(self, symbol, qty):
        return {"id": "live-1", "status": "open", "amount": qty, "filled": 0.0}

    def market_sell(self, symbol, qty):
        return {"id": "live-2", "status": "open", "amount": qty, "filled": 0.0}


def test_live_order_must_not_be_treated_as_filled_when_exchange_reports_open():
    rules = ExchangeRulesEngine()
    broker = PaperBroker(reject_probability=0.0)
    manager = OrderManager(rules, broker)
    result = manager.buy(FakeLiveExchange(), "BTC/USDT", 0.01, 50000.0, paper=False)

    assert not result.ok
    assert result.status == "PENDING_OR_PARTIAL"
    assert result.qty == 0.0
    assert result.order_id == "live-1"


def test_order_guard_survives_manager_restore():
    rules = ExchangeRulesEngine()
    broker = PaperBroker(fee_pct=0.001, slippage_pct=0.0, reject_probability=0.0)
    manager = OrderManager(rules, broker, duplicate_window_seconds=60)
    exchange = FakeExchange()
    first = manager.buy(exchange, "BTC/USDT", 0.01, 50000.0, paper=True)
    assert first.ok
    guards = manager.export_order_guards()
    restored = OrderManager(rules, broker, duplicate_window_seconds=60)
    restored.restore_order_guards(guards)
    second = restored.buy(exchange, "BTC/USDT", 0.01, 50000.0, paper=True)
    assert not second.ok
    assert second.reason == "duplicate blocked"
