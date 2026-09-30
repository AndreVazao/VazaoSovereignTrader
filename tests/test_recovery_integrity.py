from __future__ import annotations

import json
from dataclasses import dataclass

from PC_ENGINE.core.recovery import RecoveryManager


@dataclass
class Position:
    symbol: str
    qty: float


def test_recovery_writes_integrity_and_monotonic_generation(tmp_path):
    path = tmp_path / "runtime_state.json"
    manager = RecoveryManager(path)
    manager.save_positions(
        {"BTC/USDT": Position("BTC/USDT", 1.0)},
        pending_orders={"o1": {"status": "paper"}},
    )
    first = json.loads(path.read_text(encoding="utf-8"))
    assert first["schema_version"] == 2
    assert first["generation"] == 1
    assert first["integrity_sha256"]

    manager.save_positions(
        {"BTC/USDT": Position("BTC/USDT", 2.0)},
        pending_orders={},
    )
    second = json.loads(path.read_text(encoding="utf-8"))
    assert second["generation"] == 2
    assert second["positions"]["BTC/USDT"]["qty"] == 2.0


def test_recovery_falls_back_to_last_known_good_backup(tmp_path):
    path = tmp_path / "runtime_state.json"
    manager = RecoveryManager(path)
    manager.save_positions({"BTC/USDT": Position("BTC/USDT", 1.0)})

    path.write_text(path.read_text(encoding="utf-8").replace('"qty": 1.0', '"qty": 99.0'), encoding="utf-8")

    state = manager.load_state()
    assert state["recovery_source"] == "backup"
    assert state["positions"]["BTC/USDT"]["qty"] == 1.0
    assert "integrity" in state["recovery_error"].lower()


def test_recovery_reports_broken_primary_and_valid_backup(tmp_path):
    path = tmp_path / "runtime_state.json"
    manager = RecoveryManager(path)
    manager.save_positions({"BTC/USDT": Position("BTC/USDT", 1.0)})

    path.write_text("{broken", encoding="utf-8")

    diagnostics = manager.diagnostics()
    assert diagnostics["primary_valid"] is False
    assert diagnostics["backup_valid"] is True
    assert diagnostics["recovery_source"] == "backup"
    assert diagnostics["integrity_ok"] is True


def test_recovery_fails_closed_when_both_snapshots_are_invalid(tmp_path):
    path = tmp_path / "runtime_state.json"
    manager = RecoveryManager(path)
    path.write_text("{broken", encoding="utf-8")
    manager.backup_path.write_text("{also-broken", encoding="utf-8")

    state = manager.load_state()
    assert state["recovery_source"] == "none"
    assert state["recovery_error"]


def test_recovery_clear_removes_primary_and_backup(tmp_path):
    path = tmp_path / "runtime_state.json"
    manager = RecoveryManager(path)
    manager.save_positions({})
    assert path.exists()
    assert manager.backup_path.exists()

    manager.clear()

    assert not path.exists()
    assert not manager.backup_path.exists()
