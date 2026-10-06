from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

from PC_ENGINE.core.recovery import RecoveryLockError, RecoveryManager


_WORKER = r"""
import sys
import time
from pathlib import Path

from PC_ENGINE.core.recovery import RecoveryManager

state_path = Path(sys.argv[1])
ready_path = Path(sys.argv[2])
mode = sys.argv[3]

manager = RecoveryManager(state_path)
tx = manager.prepare_reconciliation(
    {
        "positions": {},
        "pending_orders": {},
        "order_guards": {},
        "execution_intents": {},
        "financial_account": {"quote_flow": 1.0 if mode == "hold" else 2.0},
        "risk_state": {},
    }
)
ready_path.write_text(tx, encoding="utf-8")

if mode == "hold":
    time.sleep(0.75)
    manager.clear_reconciliation()
"""


def _start_worker(state_path: Path, ready_path: Path, mode: str) -> subprocess.Popen:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1])
    return subprocess.Popen(
        [sys.executable, "-c", _WORKER, str(state_path), str(ready_path), mode],
        cwd=Path(__file__).resolve().parents[1],
        env=env,
    )


def _wait_for_file(path: Path, timeout: float = 5.0) -> str:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if path.exists():
            return path.read_text(encoding="utf-8")
        time.sleep(0.02)
    raise AssertionError(f"worker did not create {path} within {timeout}s")


def test_recovery_transaction_lock_blocks_second_process_until_first_finishes(tmp_path):
    state_path = tmp_path / "runtime_state.json"
    first_ready = tmp_path / "first.ready"
    second_ready = tmp_path / "second.ready"

    first = _start_worker(state_path, first_ready, "hold")
    first_tx = _wait_for_file(first_ready)
    assert first_tx

    second = _start_worker(state_path, second_ready, "exit")

    time.sleep(0.2)
    assert not second_ready.exists()

    first.wait(timeout=5)
    assert first.returncode == 0

    second_tx = _wait_for_file(second_ready)
    assert second_tx
    second.wait(timeout=5)
    assert second.returncode == 0


def test_recovery_journal_can_be_replayed_after_process_exit(tmp_path):
    state_path = tmp_path / "runtime_state.json"
    ready = tmp_path / "worker.ready"

    worker = _start_worker(state_path, ready, "exit")
    tx = _wait_for_file(ready)
    worker.wait(timeout=5)
    assert worker.returncode == 0

    manager = RecoveryManager(state_path)
    manager.commit_reconciliation(tx)
    journal = manager.load_reconciliation_journal()
    assert journal is not None
    assert journal["transaction_id"] == tx

    manager.clear_reconciliation()

    assert manager.load_financial_account()["quote_flow"] == 2.0
    assert not manager.reconciliation_journal_path.exists()


def test_recovery_transaction_lock_is_not_reentrant(tmp_path):
    manager = RecoveryManager(tmp_path / "runtime_state.json")
    manager.prepare_reconciliation(
        {
            "positions": {},
            "pending_orders": {},
            "order_guards": {},
            "execution_intents": {},
            "financial_account": {},
            "risk_state": {},
        }
    )

    with pytest.raises(RecoveryLockError):
        manager.prepare_reconciliation(
            {
                "positions": {},
                "pending_orders": {},
                "order_guards": {},
                "execution_intents": {},
                "financial_account": {},
                "risk_state": {},
            }
        )

    manager.clear_reconciliation()
