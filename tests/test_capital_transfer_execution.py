from PC_ENGINE.core.capital_transfer_accounting import CapitalTransferAccounting
from PC_ENGINE.core.capital_transfer_execution import CapitalTransferExecutionBridge, TransferExecutionRequest
from PC_ENGINE.core.capital_transfer_intent import CapitalTransferIntentStore
from PC_ENGINE.core.capital_transfer_state import CapitalTransferStateStore
from PC_ENGINE.core.execution_fabric import ExecutionFabric, ExecutionMethod, ExecutionResult


class Adapter:
    method = ExecutionMethod.API
    def __init__(self, ok=True, verified=True): self.ok, self.verified, self.calls = ok, verified, 0
    def submit_transfer(self, request):
        self.calls += 1
        return ExecutionResult(self.ok, "SUBMITTED" if self.ok else "FAILED", self.method, external_id="tx-1" if self.ok else None)
    def verify_transfer(self, request, external_id): return self.verified


def _setup(tmp_path, enabled=True):
    intents = CapitalTransferIntentStore(tmp_path / "intents.jsonl")
    states = CapitalTransferStateStore(tmp_path / "states.jsonl")
    accounting = CapitalTransferAccounting(tmp_path / "accounting.jsonl")
    intent = intents.create(owner_id="andre", source_venue="binance", destination_venue="bingx", asset="USDT", network="TRC20", amount_quote=10, estimated_cost_quote=.1, expected_net_edge_bps=5)
    adapter = Adapter()
    bridge = CapitalTransferExecutionBridge(owner_id="andre", execution_fabric=ExecutionFabric(owner_id="andre"), intent_store=intents, state_store=states, accounting=accounting, adapters={ExecutionMethod.API: adapter}, enabled=enabled)
    return bridge, TransferExecutionRequest(intent, "binance-spot", ExecutionMethod.API), adapter, states, accounting


def test_disabled_transfer_fails_closed_without_mutating_state(tmp_path):
    bridge, request, adapter, states, accounting = _setup(tmp_path, enabled=False)
    assert bridge.submit(request=request, real_authorized=True).state == "PLANNED"
    assert states.get(request.intent.intent_id, "andre") is None
    assert accounting.snapshot(owner_id="andre")["entries"] == []
    assert adapter.calls == 0


def test_submit_then_reconcile_updates_accounting_once(tmp_path):
    bridge, request, adapter, _, accounting = _setup(tmp_path, enabled=True)
    assert bridge.submit(request=request, real_authorized=True).state == "PENDING"
    assert bridge.reconcile(request=request).state == "CONFIRMED"
    assert bridge.reconcile(request=request).state == "CONFIRMED"
    assert accounting.expected_deltas(owner_id="andre") == {"binance": {"USDT": -10.0}, "bingx": {"USDT": 10.0}}
    assert adapter.calls == 1


def test_duplicate_submit_does_not_resubmit(tmp_path):
    bridge, request, adapter, _, _ = _setup(tmp_path, enabled=True)
    assert bridge.submit(request=request, real_authorized=True).state == "PENDING"
    assert bridge.submit(request=request, real_authorized=True).state == "PENDING"
    assert adapter.calls == 1


def test_without_real_authorization_does_not_submit_or_mutate(tmp_path):
    bridge, request, adapter, states, accounting = _setup(tmp_path, enabled=True)
    assert bridge.submit(request=request, real_authorized=False).state == "PLANNED"
    assert states.get(request.intent.intent_id, "andre") is None
    assert accounting.snapshot(owner_id="andre")["entries"] == []
    assert adapter.calls == 0


def test_owner_mismatch_never_writes_other_owner_state(tmp_path):
    bridge, request, adapter, states, _ = _setup(tmp_path, enabled=True)
    intent = request.intent.__class__(**{**request.intent.__dict__, "owner_id": "diogo"})
    try:
        bridge.submit(request=TransferExecutionRequest(intent, request.account_id, request.method), real_authorized=True)
    except PermissionError:
        pass
    else:
        raise AssertionError("owner mismatch must be rejected")
    assert adapter.calls == 0
    assert states.get(request.intent.intent_id, "andre") is None


def test_confirmed_state_recovers_missing_accounting_after_restart(tmp_path):
    bridge, request, adapter, states, accounting = _setup(tmp_path, enabled=True)
    assert bridge.submit(request=request, real_authorized=True).state == "PENDING"
    states.record(intent_id=request.intent.intent_id, owner_id="andre", state="CONFIRMED", external_reference="tx-1")
    assert accounting.snapshot(owner_id="andre")["entries"] == []
    assert bridge.reconcile(request=request).state == "CONFIRMED"
    assert accounting.expected_deltas(owner_id="andre") == {"binance": {"USDT": -10.0}, "bingx": {"USDT": 10.0}}
    assert adapter.calls == 1



def test_unavailable_adapter_keeps_intent_planned(tmp_path):
    bridge, request, adapter, states, accounting = _setup(tmp_path, enabled=True)
    request = TransferExecutionRequest(request.intent, request.account_id, ExecutionMethod.BROWSER)
    result = bridge.submit(request=request, real_authorized=True)
    assert result.state == "PLANNED"
    assert states.get(request.intent.intent_id, "andre") is None
    assert accounting.snapshot(owner_id="andre")["entries"] == []
    assert adapter.calls == 0
