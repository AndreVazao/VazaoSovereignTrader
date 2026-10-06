from __future__ import annotations

import multiprocessing as mp
import time
from pathlib import Path

import pytest

from PC_ENGINE.core.recovery import RecoveryLockError, RecoveryManager


def _hold_recovery_transaction(state_path: str, ready_conn) -> None:
    manager = RecoveryManager(Path(state_path))
    tx = manager.prepare_reconciliation(
        {
            "positions": {},
            "pending_orders": {},
            "order_guards": {},
            "execution_intents": {},
            "financial_account": {"quote_flow": 1.0},
            "risk_state": {},
        }
    )
    ready_conn.send(tx)
    ready_conn.close()
    time.sleep(0.75)
    manager.clear_reconciliation()


def _prepare_and_exit(state_path: str, ready_conn) -> None:
    manager = RecoveryManager(Path(state_path))
    tx = manager.prepare_reconciliation(
        {
            "positions": {},
            "pending_orders": {},
            "order_guards": {},
            "execution_intents": {},
            "financial_account": {"quote_flow": 2.0},
            "risk_state": {},
        }
    )
    ready_conn.send(tx)
    ready_conn.close()
    # Process exit releases the OS lock, modelling a crash after durable journal preparation.


def test_recovery_transaction_lock_blocks_second_process_until_first_finishes(tmp_path):
    ctx = mp.get_context("spawn")
    first_parent, first_child = ctx.Pipe(duplex=False)
    second_parent, second_child = ctx.Pipe(duplex=False)

    state_path = tmp_path / "runtime_state.json"
    first = ctx.Process(target=_hold_recovery_transaction, args=(str(state_path), first_child))
    first.start()
    first_child.close()

    first_tx = first_parent.recv()
    assert first_tx

    second = ctx.Process(target=_prepare_and_exit, args=(str(state_path), second_child))
    second.start()
    second_child.close()

    assert not second_parent.poll(0.2)

    first.join(timeout=5)
    assert first.exitcode == 0

    assert second_parent.poll(5)
    second_tx = second_parent.recv()
    assert second_tx

    second.join(timeout=5)
    assert second.exitcode == 0


def test_recovery_journal_can_be_replayed_after_process_exit(tmp_path):
    ctx = mp.get_context("spawn")
    parent_conn, child_conn = ctx.Pipe(duplex=False)
    state_path = tmp_path / "runtime_state.json"

    worker = ctx.Process(target=_prepare_and_exit, args=(str(state_path), child_conn))
    worker.start()
    child_conn.close()

    assert parent_conn.poll(5)
    tx = parent_conn.recv()
    worker.join(timeout=5)

    assert worker.exitcode == 0

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
