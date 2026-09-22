from __future__ import annotations

import json
from pathlib import Path

from PC_ENGINE.core.recovery import RecoveryManager
from PC_ENGINE.core.engine import Position


def test_recovery_write_replaces_state_atomically(tmp_path):
    state_path = tmp_path / "runtime_state.json"
    manager = RecoveryManager(state_path=state_path)
    position = Position(
        exchange="paper",
        symbol="BTC/USDT",
        entry=100.0,
        qty=0.01,
        stop=98.0,
        take_profit=104.0,
        opened_ts=1.0,
        entry_fee=0.001,
    )

    manager.save_positions({"BTC/USDT": position}, {"pending-1": {"side": "buy"}})

    assert state_path.exists()
    assert not Path(str(state_path) + ".tmp").exists()
    payload = json.loads(state_path.read_text(encoding="utf-8"))
    assert payload["positions"]["BTC/USDT"]["qty"] == 0.01
    assert payload["pending_orders"]["pending-1"]["side"] == "buy"
