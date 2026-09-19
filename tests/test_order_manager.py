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
