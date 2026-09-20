from __future__ import annotations

import json

from PC_ENGINE.core.recovery import RecoveryManager


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
