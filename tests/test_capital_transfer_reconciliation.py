from PC_ENGINE.core.capital_transfer_reconciliation import CapitalTransferReconciliationGate


class FakeAccounting:
    def __init__(self, result=None):
        self.result = result or {"reconciled": True, "mismatch_count": 0, "mismatches": []}
        self.calls = 0

    def reconcile_deltas(self, *, owner_id, observed_deltas, tolerance):
        self.calls += 1
        return dict(self.result)


def test_missing_observations_fail_closed_and_do_not_call_accounting():
    accounting = FakeAccounting()
    gate = CapitalTransferReconciliationGate(owner_id="owner-1", accounting=accounting)

    result = gate.check(None)

    assert result["reconciled"] is False
    assert result["enforced"] is True
    assert result["reason"] == "OBSERVED_DELTAS_NOT_PROVIDED"
    assert gate.allows_routing(None) is False
    assert accounting.calls == 0


def test_empty_observations_fail_closed():
    gate = CapitalTransferReconciliationGate(owner_id="owner-1", accounting=FakeAccounting())

    result = gate.check({})

    assert result["reconciled"] is False
    assert result["enforced"] is True
    assert result["reason"] == "OBSERVED_DELTAS_EMPTY_OR_INVALID"
    assert gate.allows_routing({}) is False


def test_matching_observations_can_pass_when_accounting_confirms():
    gate = CapitalTransferReconciliationGate(owner_id="owner-1", accounting=FakeAccounting())

    result = gate.check({"transfer-1": {"USDT": -10.0}})

    assert result["reconciled"] is True
    assert result["enforced"] is True
    assert result["reason"] == "OK"


def test_accounting_mismatch_blocks_routing():
    accounting = FakeAccounting({"reconciled": False, "mismatch_count": 1, "mismatches": [{"asset": "USDT"}]})
    gate = CapitalTransferReconciliationGate(owner_id="owner-1", accounting=accounting)

    result = gate.check({"transfer-1": {"USDT": -10.0}})

    assert result["reconciled"] is False
    assert gate.allows_routing({"transfer-1": {"USDT": -10.0}}) is False
    assert result["reason"] == "CAPITAL_TRANSFER_RECONCILIATION_MISMATCH"
