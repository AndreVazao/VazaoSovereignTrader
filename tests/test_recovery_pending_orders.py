from __future__ import annotations

import json

from PC_ENGINE.core.recovery import RecoveryManager


def test_recovery_persists_pending_orders(tmp_path):
    path = tmp_path / "runtime_state.json"
    recovery = RecoveryManager(path)
    recovery.save_positions(
        {"BTC/USDT": type("P", (), {"__dict__": {"symbol": "BTC/USDT"}})()},
        {"order-1": {"symbol": "BTC/USDT", "side": "buy", "requested_qty": 0.1}},
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["pending_orders"]["order-1"]["symbol"] == "BTC/USDT"
    assert recovery.load_pending_orders()["order-1"]["side"] == "buy"
