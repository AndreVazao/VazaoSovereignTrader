from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from PC_ENGINE.core.capital_transfer_planner import CapitalRouteCandidate, CapitalTransferPlanner
from PC_ENGINE.core.compounding import GlobalCompoundingOrchestrator


@dataclass(frozen=True)
class CompoundingRoutePlan:
    owner_id: str
    global_base: float
    next_base: float
    all_venues_at_base: bool
    candidates: tuple[CapitalRouteCandidate, ...]


class CompoundingRoutingBridge:
    """Bridge global compounding targets into the existing gated transfer planner.

    The compounding layer only creates a funding need. CapitalTransferPlanner
    remains the authority for whitelist, owner, reserve, economics, network and
    settlement constraints. This bridge never executes a transfer.
    """

    def __init__(self, *, orchestrator: GlobalCompoundingOrchestrator, planner: CapitalTransferPlanner):
        if orchestrator.owner_id != planner.policy.owner_id:
            raise ValueError("owner mismatch")
        self.orchestrator = orchestrator
        self.planner = planner

    def plan(
        self,
        *,
        owner_id: str,
        venues: list[dict[str, Any]],
        opportunities: list[dict[str, Any]],
    ) -> CompoundingRoutePlan:
        if owner_id != self.orchestrator.owner_id:
            return CompoundingRoutePlan(owner_id=owner_id, global_base=0.0, next_base=0.0,
                                        all_venues_at_base=False, candidates=())

        equities = {
            str(v.get("venue_id", "")).lower(): float(v.get("equity_quote", 0) or 0)
            for v in venues
            if str(v.get("venue_id", "")).strip()
        }
        snapshot = self.orchestrator.snapshot(equities)
        funding = self.orchestrator.funding_plan(equities)

        by_destination = {
            str(item["destination_venue"]).lower(): float(item["amount"])
            for item in funding
        }
        bridged: list[dict[str, Any]] = []
        for opportunity in opportunities:
            destination = str(opportunity.get("destination_venue", "")).lower()
            need = by_destination.get(destination, 0.0)
            if need <= 0:
                continue
            item = dict(opportunity)
            requested = float(item.get("required_quote", 0) or 0)
            item["required_quote"] = min(requested, need) if requested > 0 else need
            item["compounding_global_base"] = snapshot.global_base
            item["compounding_reason"] = "GLOBAL_TIER_CAPITALIZATION"
            bridged.append(item)

        candidates = tuple(
            self.planner.plan(owner_id=owner_id, venues=venues, opportunities=bridged)
        )
        return CompoundingRoutePlan(
            owner_id=owner_id,
            global_base=snapshot.global_base,
            next_base=snapshot.next_base,
            all_venues_at_base=snapshot.all_venues_at_base,
            candidates=candidates,
        )
