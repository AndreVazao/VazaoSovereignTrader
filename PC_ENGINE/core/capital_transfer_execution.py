from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from PC_ENGINE.core.capital_transfer_intent import CapitalTransferIntent, CapitalTransferIntentStore
from PC_ENGINE.core.capital_transfer_state import CapitalTransferState, CapitalTransferStateStore
from PC_ENGINE.core.execution_fabric import ExecutionFabric, ExecutionIntent, ExecutionMethod, ExecutionResult


@dataclass(frozen=True)
class TransferExecutionRequest:
    intent: CapitalTransferIntent
    account_id: str
    method: ExecutionMethod
    symbol: str = "USDT"


class TransferVenueAdapter(Protocol):
    method: ExecutionMethod

    def submit_transfer(self, request: TransferExecutionRequest) -> ExecutionResult: ...
    def verify_transfer(self, request: TransferExecutionRequest, external_id: str | None) -> bool: ...


class CapitalTransferExecutionBridge:
    """Crash-safe bridge from durable transfer intents to execution fabric.

    It is fail-closed: the caller must provide an already-approved intent and
    an owner-matching account. The bridge persists SUBMITTED/PENDING before
    waiting for verification and never treats submission as confirmation.
    """

    def __init__(
        self,
        *,
        owner_id: str,
        execution_fabric: ExecutionFabric,
        intent_store: CapitalTransferIntentStore,
        state_store: CapitalTransferStateStore,
        adapters: dict[ExecutionMethod, TransferVenueAdapter],
        enabled: bool = False,
    ):
        self.owner_id = owner_id
        self.execution_fabric = execution_fabric
        self.intent_store = intent_store
        self.state_store = state_store
        self.adapters = dict(adapters)
        self.enabled = enabled

    def submit(
        self,
        *,
        request: TransferExecutionRequest,
        real_authorized: bool = False,
    ) -> CapitalTransferState:
        intent = request.intent
        if not self.enabled or not real_authorized:
            return self.state_store.record(
                intent_id=intent.intent_id, owner_id=self.owner_id,
                state="FAILED", reason="TRANSFER_EXECUTION_DISABLED_OR_UNAUTHORIZED",
            )
        if intent.owner_id != self.owner_id:
            return self.state_store.record(
                intent_id=intent.intent_id, owner_id=self.owner_id,
                state="FAILED", reason="OWNER_MISMATCH",
            )
        if request.method not in self.adapters:
            return self.state_store.record(
                intent_id=intent.intent_id, owner_id=self.owner_id,
                state="FAILED", reason="TRANSFER_ADAPTER_UNAVAILABLE",
            )

        current = self.state_store.get(intent.intent_id, self.owner_id)
        if current and current.state in {"SUBMITTED", "PENDING", "CONFIRMED"}:
            return current

        self.state_store.record(intent_id=intent.intent_id, owner_id=self.owner_id, state="APPROVED")
        execution = self.adapters[request.method].submit_transfer(request)
        if not execution.success:
            return self.state_store.record(
                intent_id=intent.intent_id, owner_id=self.owner_id,
                state="SUBMITTED" if execution.status == "SUBMITTED" else "FAILED",
                external_reference=execution.external_id, reason=execution.reason,
            )
        self.state_store.record(
            intent_id=intent.intent_id, owner_id=self.owner_id,
            state="SUBMITTED", external_reference=execution.external_id,
        )
        return self.state_store.record(
            intent_id=intent.intent_id, owner_id=self.owner_id,
            state="PENDING", external_reference=execution.external_id,
        )

    def reconcile(self, *, request: TransferExecutionRequest) -> CapitalTransferState:
        current = self.state_store.get(request.intent.intent_id, self.owner_id)
        if not current:
            return self.state_store.record(
                intent_id=request.intent.intent_id, owner_id=self.owner_id,
                state="FAILED", reason="MISSING_TRANSFER_STATE",
            )
        if current.state == "CONFIRMED":
            return current
        if current.state != "PENDING":
            return current
        verified = self.adapters[request.method].verify_transfer(
            request, current.external_reference
        )
        if verified:
            return self.state_store.record(
                intent_id=request.intent.intent_id, owner_id=self.owner_id,
                state="CONFIRMED", external_reference=current.external_reference,
            )
        return current

    @staticmethod
    def snapshot(*, enabled: bool) -> dict[str, Any]:
        return {
            "owner_private": True,
            "execution_authority": "APPROVED_INTENT_ONLY",
            "enabled": bool(enabled),
            "confirmation_requires_venue_verification": True,
        }
