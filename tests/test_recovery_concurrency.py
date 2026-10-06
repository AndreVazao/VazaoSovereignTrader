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


def test_prepare_allows_only_one_concurrent_journal_creator(tmp_path):
    from concurrent.futures import ThreadPoolExecutor

    state_path = tmp_path / "runtime_state.json"

    def prepare(marker: str):
        manager = RecoveryManager(state_path=state_path)
        try:
            return ("ok", manager.prepare_reconciliation(target_state(marker)))
        except RecoveryConcurrencyError as exc:
            return ("conflict", str(exc))

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(prepare, ("first", "second")))

    assert [result[0] for result in results].count("ok") == 1
    assert [result[0] for result in results].count("conflict") == 1

    journal = RecoveryManager(state_path=state_path).load_reconciliation_journal()
    assert journal is not None
    assert journal["target_state"]["pending_orders"]["marker"]["value"] in {"first", "second"}


def test_pending_reconciliation_replays_after_restart(tmp_path):
    state_path = tmp_path / "runtime_state.json"
    manager = RecoveryManager(state_path=state_path)
    transaction_id = manager.prepare_reconciliation(target_state("restart"))

    restarted = RecoveryManager(state_path=state_path)
    assert restarted.recover_pending_reconciliation() == transaction_id
    assert restarted.load_pending_orders()["marker"]["value"] == "restart"
    assert restarted.load_reconciliation_journal() is None

    restarted.recover_pending_reconciliation()
    assert restarted.load_pending_orders()["marker"]["value"] == "restart"


def test_pending_reconciliation_repairs_primary_from_backup(tmp_path):
    state_path = tmp_path / "runtime_state.json"
    manager = RecoveryManager(state_path=state_path)
    manager.save_positions({}, risk_state={"stable": True})
    transaction_id = manager.prepare_reconciliation(target_state("repair"))

    manager.commit_reconciliation(transaction_id)
    state_path.write_text("{broken-json", encoding="utf-8")

    restarted = RecoveryManager(state_path=state_path)
    assert restarted.recover_pending_reconciliation() == transaction_id
    recovered = restarted.load_state()
    assert recovered["pending_orders"]["marker"]["value"] == "repair"
    assert recovered["recovery_source"] == "primary"
    assert restarted.load_reconciliation_journal() is None
