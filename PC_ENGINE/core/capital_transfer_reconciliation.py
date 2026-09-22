from __future__ import annotations

from typing import Any

from PC_ENGINE.core.capital_transfer_accounting import CapitalTransferAccounting


class CapitalTransferReconciliationGate:
    """Owner-private fail-closed gate for routing after confirmed transfers."""

    def __init__(self, *, owner_id: str, accounting: CapitalTransferAccounting, tolerance: float = 1e-8):
        self.owner_id = str(owner_id or "").strip().lower()
        self.accounting = accounting
        self.tolerance = max(0.0, float(tolerance))
        if not self.owner_id:
            raise ValueError("owner_id is required")

    def check(self, observed_deltas: dict[str, dict[str, float]] | None) -> dict[str, Any]:
        if observed_deltas is None:
            return {
                "owner_private": True,
                "reconciled": True,
                "enforced": False,
                "reason": "OBSERVED_DELTAS_NOT_PROVIDED",
                "mismatch_count": 0,
                "mismatches": [],
            }
        result = self.accounting.reconcile_deltas(
            owner_id=self.owner_id,
            observed_deltas=observed_deltas,
            tolerance=self.tolerance,
        )
        return {
            **result,
            "enforced": True,
            "reason": "OK" if result["reconciled"] else "CAPITAL_TRANSFER_RECONCILIATION_MISMATCH",
        }

    def allows_routing(self, observed_deltas: dict[str, dict[str, float]] | None) -> bool:
        return bool(self.check(observed_deltas)["reconciled"])
