from __future__ import annotations

import json

from PC_ENGINE.core.recovery import RecoveryManager
from PC_ENGINE.core.engine import RuntimeState, SovereignEngine


def test_recovery_persists_pending_orders(tmp_path):
    path = tmp_path / "runtime_state.json"
    recovery = RecoveryManager(path)
    recovery.save_positions(
        {},
        {"order-1": {"symbol": "BTC/USDT", "side": "buy", "requested_qty": 0.1}},
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["pending_orders"]["order-1"]["symbol"] == "BTC/USDT"
    assert recovery.load_pending_orders()["order-1"]["side"] == "buy"


def test_recovery_persists_order_guards(tmp_path):
    path = tmp_path / "runtime_state.json"
    recovery = RecoveryManager(path)
    recovery.save_positions({}, {}, {"fake:BTC/USDT:buy:0.01:100.0": 123.0})
    assert recovery.load_order_guards()["fake:BTC/USDT:buy:0.01:100.0"] == 123.0


def test_recovery_persists_execution_intents_atomically(tmp_path):
    path = tmp_path / "runtime_state.json"
    recovery = RecoveryManager(path)
    recovery.save_positions({}, {}, {}, {"intent-1": {"symbol": "BTC/USDT", "side": "buy", "requested_qty": 0.1}})
    assert recovery.load_execution_intents()["intent-1"]["side"] == "buy"
    assert not (tmp_path / "runtime_state.json.tmp").exists()



def test_recovery_execution_intent_blocks_engine_start():
    import threading

    engine = object.__new__(SovereignEngine)
    engine.thread = None
    engine.state = RuntimeState(status="SAFE_MODE", mode="REAL", execution_intents={"intent-1": {"symbol": "BTC/USDT"}})
    engine.config = {"engine": {"preflight_required": False}, "research": {"enabled": False}}
    engine.stop_event = threading.Event()
    engine.research_stop_event = threading.Event()
    engine.paper = False
    engine.paper_collector = None
    engine.research_thread = None
    engine.run_preflight = lambda: {"ok": True}
    logs = []
    engine.log = lambda message, data=None: logs.append((message, data))

    engine.start()

    assert engine.state.status == "SAFE_MODE"
    assert engine.thread is None
    assert logs[-1][0] == "RECOVERY_UNRESOLVED_EXECUTION_INTENTS_BLOCK_START"



def test_unresolved_intent_recovers_unique_open_order():
    import threading

    class Exchange:
        name = "binance"
        def fetch_open_orders(self, symbol=None):
            return [{"id": "ex-123", "symbol": "BTC/USDT", "side": "buy", "amount": 0.1, "filled": 0.0, "price": 100.0, "status": "open"}]

    engine = object.__new__(SovereignEngine)
    engine.paper = False
    engine.state = RuntimeState(execution_intents={"intent-1": {"exchange": "binance", "symbol": "BTC/USDT", "side": "buy", "requested_qty": 0.1, "reference_price": 100.0, "created_ts": 1.0}})
    engine._main_exchange = lambda: Exchange()
    engine._persist_recovery = lambda: None
    engine.log = lambda *args, **kwargs: None

    engine._recover_unresolved_execution_intents()

    assert engine.state.execution_intents == {}
    assert engine.state.pending_orders["ex-123"]["recovered_from_intent"] == "intent-1"


def test_unresolved_intent_does_not_guess_when_open_orders_are_ambiguous():
    class Exchange:
        name = "binance"
        def fetch_open_orders(self, symbol=None):
            return [
                {"id": "ex-1", "symbol": "BTC/USDT", "side": "buy", "amount": 0.1},
                {"id": "ex-2", "symbol": "BTC/USDT", "side": "buy", "amount": 0.1},
            ]

    engine = object.__new__(SovereignEngine)
    engine.paper = False
    engine.state = RuntimeState(execution_intents={"intent-1": {"symbol": "BTC/USDT", "side": "buy", "requested_qty": 0.1}})
    engine._main_exchange = lambda: Exchange()
    engine._persist_recovery = lambda: None
    engine.log = lambda *args, **kwargs: None

    engine._recover_unresolved_execution_intents()

    assert "intent-1" in engine.state.execution_intents
    assert engine.state.pending_orders == {}
