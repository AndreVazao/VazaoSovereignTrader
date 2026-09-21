from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from PC_ENGINE.core.capital_transfer_accounting import CapitalTransferAccounting
from PC_ENGINE.core.compounding import GlobalCompoundingOrchestrator


@dataclass(frozen=True)
class CapitalCompoundingControl:
    owner_id: str
    reconciliation: dict[str, Any]
    compounding: dict[str, Any]
    routing_allowed: bool
    reason: str


class CapitalCompoundingController:
    """Owner-private gate between confirmed transfer accounting and compounding.

    Observed venue equity remains the source of truth. Transfer accounting is
    used as a reconciliation gate, never as a second balance source, avoiding
    double-counting confirmed transfers.
    """

    def __init__(
        self,
        *,
        owner_id: str,
        accounting: CapitalTransferAccounting,
        orchestrator: GlobalCompoundingOrchestrator,
    ):
        self.owner_id = str(owner_id or "").strip().lower()
        self.accounting = accounting
        self.orchestrator = orchestrator
        if not self.owner_id:
            raise ValueError("owner_id is required")
        if orchestrator.owner_id != self.owner_id:
            raise PermissionError("orchestrator belongs to another owner")

    def evaluate(
        self,
        *,
        observed_deltas: dict[str, dict[str, float]],
        equities: dict[str, float],
    ) -> CapitalCompoundingControl:
        reconciliation = self.accounting.reconcile_deltas(
            owner_id=self.owner_id,
            observed_deltas=observed_deltas,
        )
        if not reconciliation["reconciled"]:
            return CapitalCompoundingControl(
                owner_id=self.owner_id,
                reconciliation=reconciliation,
                compounding={"owner_private": True, "status": "BLOCKED"},
                routing_allowed=False,
                reason="CAPITAL_RECONCILIATION_MISMATCH",
            )

        snapshot = self.orchestrator.snapshot(equities)
        return CapitalCompoundingControl(
            owner_id=self.owner_id,
            reconciliation=reconciliation,
            compounding={
                "owner_private": True,
                "status": "READY",
                "global_base": snapshot.global_base,
                "next_base": snapshot.next_base,
                "total_equity": snapshot.total_equity,
                "all_venues_at_base": snapshot.all_venues_at_base,
                "funding_plan": self.orchestrator.funding_plan(equities),
            },
            routing_allowed=True,
            reason="CAPITAL_RECONCILED",
        )

    @staticmethod
    def snapshot(result: CapitalCompoundingControl) -> dict[str, Any]:
        return {
            "owner_private": True,
            "execution_authority": "NONE",
            "routing_allowed": result.routing_allowed,
            "reason": result.reason,
            "reconciliation": result.reconciliation,
            "compounding": result.compounding,
        }
