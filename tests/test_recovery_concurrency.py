from __future__ import annotations

import pytest

from PC_ENGINE.core.recovery import RecoveryConcurrencyError, RecoveryManager


def target_state(marker: str) -> dict:
    return {
        "positions": {},
        "pending_orders": {"marker": {"value": marker}},
        "order_guards": {},
        "execution_intents": {},
        "financial_account": {},
        "risk_state": {},
    }


def test_prepare_refuses_overwrite_pending_transaction(tmp_path):
    manager = RecoveryManager(state_path=tmp_path / "runtime_state.json")
    transaction_id = manager.prepare_reconciliation(target_state("first"))

    with pytest.raises(RecoveryConcurrencyError, match="already pending"):
        manager.prepare_reconciliation(target_state("second"))

    journal = manager.load_reconciliation_journal()
    assert journal is not None
    assert journal["transaction_id"] == transaction_id
    assert journal["target_state"]["pending_orders"]["marker"]["value"] == "first"


def test_commit_is_idempotent_for_same_transaction(tmp_path):
    manager = RecoveryManager(state_path=tmp_path / "runtime_state.json")
    transaction_id = manager.prepare_reconciliation(target_state("first"))

    manager.commit_reconciliation(transaction_id)
    manager.commit_reconciliation(transaction_id)

    state = manager.load_state()
    assert state["pending_orders"]["marker"]["value"] == "first"
    assert state["recovery_generation"] == 1


def test_commit_refuses_stale_generation(tmp_path):
    state_path = tmp_path / "runtime_state.json"
    manager = RecoveryManager(state_path=state_path)
    manager.save_positions({})

    transaction_id = manager.prepare_reconciliation(target_state("transaction"))
    manager.save_positions({}, risk_state={"winner": "newer"})

    with pytest.raises(RecoveryConcurrencyError, match="generation conflict"):
        manager.commit_reconciliation(transaction_id)

    assert manager.load_state()["risk_state"] == {"winner": "newer"}
