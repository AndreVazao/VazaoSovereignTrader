from PC_ENGINE.core.capital_transfer_execution import (
    CapitalTransferExecutionBridge, TransferExecutionRequest,
)
from PC_ENGINE.core.capital_transfer_intent import CapitalTransferIntentStore
from PC_ENGINE.core.capital_transfer_state import CapitalTransferStateStore
from PC_ENGINE.core.execution_fabric import ExecutionFabric, ExecutionMethod, ExecutionResult


class Adapter:
    method = ExecutionMethod.API
    def __init__(self, ok=True, verified=True):
        self.ok, self.verified = ok, verified
        self.calls = 0
    def submit_transfer(self, request):
        self.calls += 1
        return ExecutionResult(self.ok, "SUBMITTED" if self.ok else "FAILED",
                               self.method, external_id="tx-1" if self.ok else None)
    def verify_transfer(self, request, external_id):
        return self.verified


def _setup(tmp_path, enabled=True):
    intents = CapitalTransferIntentStore(tmp_path / "intents.jsonl")
    states = CapitalTransferStateStore(tmp_path / "states.jsonl")
    intent = intents.create(owner_id="andre", source_venue="binance",
        destination_venue="bingx", asset="USDT", network="TRC20",
        amount_quote=10, estimated_cost_quote=.1, expected_net_edge_bps=5)
    adapter = Adapter()
    bridge = CapitalTransferExecutionBridge(owner_id="andre",
        execution_fabric=ExecutionFabric(owner_id="andre"),
        intent_store=intents, state_store=states,
        adapters={ExecutionMethod.API: adapter}, enabled=enabled)
    return bridge, TransferExecutionRequest(intent, "binance-spot", ExecutionMethod.API), adapter


def test_disabled_transfer_fails_closed(tmp_path):
    bridge, request, adapter = _setup(tmp_path, enabled=False)
    state = bridge.submit(request=request, real_authorized=True)
    assert state.state == "FAILED"
    assert adapter.calls == 0


def test_submit_then_reconcile(tmp_path):
    bridge, request, adapter = _setup(tmp_path, enabled=True)
    state = bridge.submit(request=request, real_authorized=True)
    assert state.state == "PENDING"
    assert bridge.reconcile(request=request).state == "CONFIRMED"
    assert adapter.calls == 1


def test_duplicate_submit_does_not_resubmit(tmp_path):
    bridge, request, adapter = _setup(tmp_path, enabled=True)
    assert bridge.submit(request=request, real_authorized=True).state == "PENDING"
    assert bridge.submit(request=request, real_authorized=True).state == "PENDING"
    assert adapter.calls == 1


def test_without_real_authorization_does_not_submit(tmp_path):
    bridge, request, adapter = _setup(tmp_path, enabled=True)
    assert bridge.submit(request=request, real_authorized=False).state == "FAILED"
    assert adapter.calls == 0
