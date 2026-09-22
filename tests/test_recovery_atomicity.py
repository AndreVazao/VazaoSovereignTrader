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


def test_corrupt_recovery_state_is_detectable(tmp_path):
    state_path = tmp_path / "runtime_state.json"
    state_path.write_text("{broken-json", encoding="utf-8")

    manager = RecoveryManager(state_path=state_path)
    state = manager.load_state()

    assert state["positions"] == {}
    assert state["pending_orders"] == {}
    assert "recovery_error" in state
    assert state["recovery_error"]


def test_pending_fill_recovery_markers_survive_restart(tmp_path):
    state_path = tmp_path / "runtime_state.json"
    manager = RecoveryManager(state_path=state_path)

    manager.save_positions(
        {},
        {
            "order-1": {
                "symbol": "BTC/USDT",
                "side": "buy",
                "requested_qty": 1.0,
                "known_filled_qty": 0.4,
                "known_fill_price": 100.0,
                "known_quote_notional": 40.0,
                "known_fee": 0.04,
            }
        },
    )

    recovered = RecoveryManager(state_path=state_path).load_pending_orders()
    item = recovered["order-1"]

    assert item["known_filled_qty"] == 0.4
    assert item["known_quote_notional"] == 40.0
    assert item["known_fee"] == 0.04
