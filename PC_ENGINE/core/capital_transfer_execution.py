from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from PC_ENGINE.core.capital_transfer_accounting import CapitalTransferAccounting
from PC_ENGINE.core.capital_transfer_intent import CapitalTransferIntent, CapitalTransferIntentStore
from PC_ENGINE.core.capital_transfer_state import CapitalTransferState, CapitalTransferStateStore
from PC_ENGINE.core.execution_fabric import ExecutionFabric, ExecutionMethod, ExecutionResult


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
    """Crash-safe bridge from approved intents to verified transfer accounting."""

    def __init__(self, *, owner_id: str, execution_fabric: ExecutionFabric, intent_store: CapitalTransferIntentStore,
                 state_store: CapitalTransferStateStore, adapters: dict[ExecutionMethod, TransferVenueAdapter],
                 accounting: CapitalTransferAccounting | None = None, enabled: bool = False):
        self.owner_id, self.execution_fabric, self.intent_store = owner_id, execution_fabric, intent_store
        self.state_store, self.adapters, self.accounting = state_store, dict(adapters), accounting
        self.enabled = enabled

    def submit(self, *, request: TransferExecutionRequest, real_authorized: bool = False) -> CapitalTransferState:
        intent = request.intent
        if intent.owner_id != self.owner_id:
            raise PermissionError("transfer intent belongs to another owner")
        current = self.state_store.get(intent.intent_id, self.owner_id)
        if current and current.state in {"SUBMITTED", "PENDING", "CONFIRMED"}:
            return current
        if not self.enabled or not real_authorized:
            return current or CapitalTransferState(intent.intent_id, self.owner_id, "PLANNED", intent.created_at_ms)
        if request.method not in self.adapters:
            return current or CapitalTransferState(intent.intent_id, self.owner_id, "PLANNED", intent.created_at_ms)
        if current and current.state not in {"PLANNED", "APPROVED"}:
            return current
        if not current or current.state == "PLANNED":
            self.state_store.record(intent_id=intent.intent_id, owner_id=self.owner_id, state="APPROVED")
        execution = self.adapters[request.method].submit_transfer(request)
        if not execution.success:
            return self.state_store.record(intent_id=intent.intent_id, owner_id=self.owner_id,
                state="SUBMITTED" if execution.status == "SUBMITTED" else "FAILED",
                external_reference=execution.external_id, reason=execution.reason)
        self.state_store.record(intent_id=intent.intent_id, owner_id=self.owner_id, state="SUBMITTED", external_reference=execution.external_id)
        return self.state_store.record(intent_id=intent.intent_id, owner_id=self.owner_id, state="PENDING", external_reference=execution.external_id)

    def _apply_accounting(self, request: TransferExecutionRequest, external_reference: str | None) -> None:
        if self.accounting is None:
            return
        self.accounting.apply_confirmed(
            intent_id=request.intent.intent_id,
            owner_id=self.owner_id,
            source_venue=request.intent.source_venue,
            destination_venue=request.intent.destination_venue,
            asset=request.intent.asset,
            amount=request.intent.amount_quote,
            external_reference=external_reference,
        )

    def reconcile(self, *, request: TransferExecutionRequest) -> CapitalTransferState:
        if request.intent.owner_id != self.owner_id:
            raise PermissionError("transfer intent belongs to another owner")
        current = self.state_store.get(request.intent.intent_id, self.owner_id)
        if not current:
            return self.state_store.record(intent_id=request.intent.intent_id, owner_id=self.owner_id, state="FAILED", reason="MISSING_TRANSFER_STATE")
        if current.state == "CONFIRMED":
            self._apply_accounting(request, current.external_reference)
            return current
        if current.state != "PENDING":
            return current
        adapter = self.adapters.get(request.method)
        if adapter is None or not adapter.verify_transfer(request, current.external_reference):
            return current
        confirmed = self.state_store.record(intent_id=request.intent.intent_id, owner_id=self.owner_id,
            state="CONFIRMED", external_reference=current.external_reference)
        self._apply_accounting(request, current.external_reference)
        return confirmed

    @staticmethod
    def snapshot(*, enabled: bool) -> dict[str, Any]:
        return {
            "owner_private": True,
            "execution_authority": "APPROVED_INTENT_ONLY",
            "enabled": bool(enabled),
            "confirmation_requires_venue_verification": True,
            "confirmed_transfer_accounting": True,
        }
