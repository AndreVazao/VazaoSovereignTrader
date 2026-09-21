from __future__ import annotations

from PC_ENGINE.core.engine import Position, RuntimeState, SovereignEngine
from PC_ENGINE.core.recovery import RecoveryManager


class FakeExchange:
    name = "binance"

    def __init__(self, responses):
        self.responses = list(responses)

    def fetch_order(self, order_id, symbol):
        if not self.responses:
            raise AssertionError("unexpected extra fetch_order")
        return self.responses.pop(0)


class RiskStub:
    def __init__(self):
        self.results = []

    def record_trade_result(self, symbol, pnl_pct):
        self.results.append((symbol, pnl_pct))


class ChampionStub:
    def __init__(self):
        self.results = []

    def record(self, *args, **kwargs):
        self.results.append((args, kwargs))


class LedgerStub:
    def __init__(self):
        self.trades = []

    def trade(self, payload):
        self.trades.append(payload)


def make_engine(exchange):
    engine = object.__new__(SovereignEngine)
    engine.paper = False
    engine.config = {"reconciliation": {"financial_relative_tolerance": 0.002}}
    engine.state = RuntimeState()
    engine.state.pending_orders = {
        "o1": {
            "exchange": "binance",
            "symbol": "BTC/USDT",
            "side": "buy",
            "requested_qty": 1.0,
            "known_filled_qty": 0.0,
            "known_fill_price": 100.0,
            "known_fee": 0.0,
            "known_quote_notional": 0.0,
            "created_ts": 1.0,
            "client_order_id": "cid-1",
            "stop_pct": 0.02,
            "take_profit_pct": 0.04,
        }
    }
    engine._main_exchange = lambda: exchange
    engine._persist_recovery = lambda: None
    engine.log = lambda *args, **kwargs: None
    engine.risk = RiskStub()
    engine.champion = ChampionStub()
    engine.ledger = LedgerStub()
    return engine


def test_partial_buy_applies_observed_fill_once_and_tracks_financial_flow():
    exchange = FakeExchange([
        {
            "id": "o1", "clientOrderId": "cid-1", "symbol": "BTC/USDT",
            "side": "buy", "status": "open", "filled": 0.4,
            "average": 100.0, "cost": 40.0, "fee": {"cost": 0.04, "currency": "USDT"},
        },
        {
            "id": "o1", "clientOrderId": "cid-1", "symbol": "BTC/USDT",
            "side": "buy", "status": "closed", "filled": 1.0,
            "average": 102.0, "cost": 102.0, "fee": {"cost": 0.10, "currency": "USDT"},
        },
    ])
    engine = make_engine(exchange)

    engine._reconcile_pending_orders()
    first = engine.state.open_positions["BTC/USDT"]
    assert first.qty == 0.4
    assert first.entry == 100.0
    assert engine.state.financial_account["base_flow"]["BTC"] == 0.4
    assert engine.state.financial_account["quote_flow"] == -40.04

    engine._reconcile_pending_orders()
    assert "o1" not in engine.state.pending_orders
    position = engine.state.open_positions["BTC/USDT"]
    assert position.qty == 1.0
    assert abs(position.entry - 102.0) < 1e-12
    assert engine.state.financial_account["base_flow"]["BTC"] == 1.0
    assert abs(engine.state.financial_account["quote_flow"] + 102.10) < 1e-12


def test_partial_sell_applies_incremental_notional_and_closes_position():
    exchange = FakeExchange([
        {
            "id": "o1", "clientOrderId": "cid-1", "symbol": "BTC/USDT",
            "side": "sell", "status": "open", "filled": 0.4,
            "average": 100.0, "cost": 40.0, "fee": {"cost": 0.04, "currency": "USDT"},
        },
        {
            "id": "o1", "clientOrderId": "cid-1", "symbol": "BTC/USDT",
            "side": "sell", "status": "closed", "filled": 1.0,
            "average": 105.0, "cost": 105.0, "fee": {"cost": 0.10, "currency": "USDT"},
        },
    ])
    engine = make_engine(exchange)
    engine.state.open_positions["BTC/USDT"] = Position(
        "binance", "BTC/USDT", 100.0, 1.0, 98.0, 104.0, 1.0, 0.10
    )
    engine.state.pending_orders["o1"].update({
        "side": "sell",
        "stop_pct": 0.0,
        "take_profit_pct": 0.0,
    })

    engine._reconcile_pending_orders()
    assert engine.state.open_positions["BTC/USDT"].qty == 0.6
    assert engine.state.financial_account["base_flow"]["BTC"] == -0.4
    assert abs(engine.state.financial_account["quote_flow"] - 39.96) < 1e-12

    engine._reconcile_pending_orders()
    assert "BTC/USDT" not in engine.state.open_positions
    assert "o1" not in engine.state.pending_orders
    assert engine.state.financial_account["base_flow"]["BTC"] == -1.0
    assert abs(engine.state.financial_account["quote_flow"] - 104.90) < 1e-12
    assert len(engine.ledger.trades) == 2


def test_recovery_load_error_keeps_financial_account_key():
    manager = object.__new__(RecoveryManager)
    manager.state_path = None

    class BrokenPath:
        def exists(self):
            return True

        def read_text(self, encoding=None):
            raise ValueError("broken")

    manager.state_path = BrokenPath()
    state = manager.load_state()
    assert state["financial_account"] == {}


def test_restart_after_partial_fill_applies_only_remaining_delta(tmp_path):
    recovery = RecoveryManager(tmp_path / "runtime_state.json")
    first = object.__new__(SovereignEngine)
    first.paper = False
    first.state = RuntimeState()
    first.state.open_positions["BTC/USDT"] = Position(
        "binance", "BTC/USDT", 100.0, 0.4, 98.0, 104.0, 1.0, 0.04
    )
    first.state.pending_orders["o1"] = {
        "exchange": "binance",
        "symbol": "BTC/USDT",
        "side": "buy",
        "requested_qty": 1.0,
        "known_filled_qty": 0.4,
        "known_fill_price": 100.0,
        "known_fee": 0.04,
        "known_quote_notional": 40.0,
        "created_ts": 1.0,
        "client_order_id": "cid-1",
        "stop_pct": 0.02,
        "take_profit_pct": 0.04,
    }
    first.state.financial_account = {
        "base_flow": {"BTC": 0.4},
        "quote_flow": -40.04,
    }
    recovery.save_positions(
        first.state.open_positions,
        first.state.pending_orders,
        {},
        {},
        first.state.financial_account,
    )

    second = object.__new__(SovereignEngine)
    second.paper = False
    second.state = RuntimeState()
    second.recovery = recovery

    class OrderGuardStub:
        def restore_order_guards(self, guards):
            assert guards == {}

    second.order_manager = OrderGuardStub()
    second.log = lambda *args, **kwargs: None
    second._load_recovery_state()

    class RestartExchange(FakeExchange):
        name = "binance"

    second._main_exchange = lambda: RestartExchange([{
        "id": "o1", "clientOrderId": "cid-1", "symbol": "BTC/USDT",
        "side": "buy", "status": "closed", "filled": 1.0,
        "average": 102.0, "cost": 102.0,
        "fee": {"cost": 0.10, "currency": "USDT"},
    }])
    second.config = {"reconciliation": {"financial_relative_tolerance": 0.002}}
    second._persist_recovery = lambda: None
    second.log = lambda *args, **kwargs: None
    second.risk = RiskStub()
    second.champion = ChampionStub()
    second.ledger = LedgerStub()

    second._reconcile_pending_orders()

    assert "o1" not in second.state.pending_orders
    position = second.state.open_positions["BTC/USDT"]
    assert position.qty == 1.0
    assert abs(position.entry - 101.2) < 1e-12
    assert second.state.financial_account["base_flow"]["BTC"] == 1.0
    assert abs(second.state.financial_account["quote_flow"] + 102.10) < 1e-12


def test_restart_after_partial_sell_applies_only_remaining_delta_once(tmp_path):
    recovery = RecoveryManager(tmp_path / "runtime_state.json")
    first = object.__new__(SovereignEngine)
    first.paper = False
    first.state = RuntimeState()
    first.state.open_positions["BTC/USDT"] = Position(
        "binance", "BTC/USDT", 100.0, 0.6, 98.0, 104.0, 1.0, 0.06
    )
    first.state.pending_orders["o1"] = {
        "exchange": "binance", "symbol": "BTC/USDT", "side": "sell",
        "requested_qty": 1.0, "known_filled_qty": 0.4,
        "known_fill_price": 100.0, "known_fee": 0.04,
        "known_quote_notional": 40.0, "created_ts": 1.0,
        "client_order_id": "cid-1",
    }
    first.state.financial_account = {
        "base_flow": {"BTC": -0.4}, "quote_flow": 39.96,
    }
    recovery.save_positions(first.state.open_positions, first.state.pending_orders, {}, {}, first.state.financial_account)

    second = object.__new__(SovereignEngine)
    second.paper = False
    second.state = RuntimeState()
    second.recovery = recovery

    class OrderGuardStub:
        def restore_order_guards(self, guards):
            assert guards == {}

    second.order_manager = OrderGuardStub()
    second.log = lambda *args, **kwargs: None
    second._load_recovery_state()
    second.config = {"reconciliation": {"financial_relative_tolerance": 0.002}}
    second._persist_recovery = lambda: None
    second.risk = RiskStub()
    second.champion = ChampionStub()
    second.ledger = LedgerStub()

    class RestartExchange(FakeExchange):
        name = "binance"

    second._main_exchange = lambda: RestartExchange([{
        "id": "o1", "clientOrderId": "cid-1", "symbol": "BTC/USDT",
        "side": "sell", "status": "closed", "filled": 1.0,
        "average": 105.0, "cost": 105.0,
        "fee": {"cost": 0.10, "currency": "USDT"},
    }])

    second._reconcile_pending_orders()

    assert "o1" not in second.state.pending_orders
    assert "BTC/USDT" not in second.state.open_positions
    assert second.state.financial_account["base_flow"]["BTC"] == -1.0
    assert abs(second.state.financial_account["quote_flow"] - 104.90) < 1e-12
    assert len(second.ledger.trades) == 1
    assert second.ledger.trades[0]["qty"] == 0.6
    assert len(second.risk.results) == 1

    second._reconcile_pending_orders()
    assert len(second.ledger.trades) == 1
    assert len(second.risk.results) == 1


def test_sell_pending_preserves_execution_intent_until_pending_is_durable():
    engine = object.__new__(SovereignEngine)
    engine.paper = False
    engine.state = RuntimeState()
    engine.state.open_positions["BTC/USDT"] = Position(
        "binance", "BTC/USDT", 100.0, 1.0, 98.0, 104.0, 1.0, 0.10
    )
    engine._persist_recovery = lambda: None
    engine.log = lambda *args, **kwargs: None
    engine.risk = RiskStub()
    engine.champion = ChampionStub()
    engine.ledger = LedgerStub()

    class PendingOrderManager:
        def sell(self, exchange, symbol, qty, price, paper, spread_pct, client_order_id):
            return type("Result", (), {
                "ok": True, "side": "sell", "symbol": symbol, "qty": 0.4,
                "price": price, "fee": 0.04, "order_id": "sell-1",
                "reason": "partial", "requested_qty": qty,
                "status": "PENDING_OR_PARTIAL",
            })()

    engine.order_manager = PendingOrderManager()

    class Exchange:
        name = "binance"

    engine._close_position(
        Exchange(), engine.state.open_positions["BTC/USDT"],
        101.0, "test", 0.0,
    )

    assert "sell-1" in engine.state.pending_orders
    assert not engine.state.execution_intents
