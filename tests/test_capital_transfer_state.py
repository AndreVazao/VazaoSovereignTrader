from PC_ENGINE.core.capital_transfer_state import CapitalTransferStateStore


def test_transfer_state_machine_is_durable_and_idempotent(tmp_path):
    store = CapitalTransferStateStore(tmp_path / "states.jsonl")
    assert store.record(intent_id="i1", owner_id="andre", state="PLANNED").state == "PLANNED"
    assert store.record(intent_id="i1", owner_id="andre", state="PLANNED").state == "PLANNED"
    store.record(intent_id="i1", owner_id="andre", state="APPROVED")
    store.record(intent_id="i1", owner_id="andre", state="SUBMITTED", external_reference="w1")
    store.record(intent_id="i1", owner_id="andre", state="PENDING", external_reference="w1")
    store.record(intent_id="i1", owner_id="andre", state="CONFIRMED", external_reference="w1")
    assert store.get("i1", "andre").state == "CONFIRMED"


def test_transfer_state_rejects_invalid_transition_and_cross_owner(tmp_path):
    store = CapitalTransferStateStore(tmp_path / "states.jsonl")
    store.record(intent_id="i1", owner_id="andre", state="PLANNED")
    try:
        store.record(intent_id="i1", owner_id="andre", state="CONFIRMED")
        assert False, "expected invalid transition"
    except ValueError:
        pass
    try:
        store.get("i1", "genro")
        assert False, "expected owner isolation"
    except PermissionError:
        pass


def test_transfer_state_allows_fail_from_pending(tmp_path):
    store = CapitalTransferStateStore(tmp_path / "states.jsonl")
    store.record(intent_id="i1", owner_id="andre", state="PLANNED")
    store.record(intent_id="i1", owner_id="andre", state="APPROVED")
    store.record(intent_id="i1", owner_id="andre", state="SUBMITTED")
    store.record(intent_id="i1", owner_id="andre", state="PENDING")
    state = store.record(intent_id="i1", owner_id="andre", state="FAILED", reason="exchange_rejected")
    assert state.reason == "exchange_rejected"
