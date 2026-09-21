from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from PC_ENGINE.core.capital_routing_policy import CapitalRoutingPolicy


@dataclass(frozen=True)
class CapitalRouteCandidate:
    source_venue: str
    destination_venue: str
    asset: str
    amount_quote: float
    expected_net_edge_bps: float
    estimated_transfer_cost_quote: float
    reason: str


class CapitalTransferPlanner:
    """Owner-private, decision-only planner for venue-to-venue capital routing.

    It consumes private venue balances plus independently measured destination
    needs/opportunities. It never transfers funds and never grants REAL authority.
    """

    def __init__(self, policy: CapitalRoutingPolicy):
        self.policy = policy

    def plan(
        self,
        *,
        owner_id: str,
        venues: list[dict[str, Any]],
        opportunities: list[dict[str, Any]],
    ) -> list[CapitalRouteCandidate]:
        self.policy.validate()
        if owner_id != self.policy.owner_id:
            return []

        by_venue = {
            str(v.get("venue_id", "")).lower(): v
            for v in venues
            if str(v.get("venue_id", "")).strip()
        }
        candidates: list[CapitalRouteCandidate] = []

        for opportunity in opportunities:
            destination = str(opportunity.get("destination_venue", "")).lower()
            asset = str(opportunity.get("asset", "USDT")).upper()
            required = float(opportunity.get("required_quote", 0) or 0)
            edge = float(opportunity.get("expected_net_edge_bps", 0) or 0)
            transfer_cost = float(opportunity.get("estimated_transfer_cost_quote", 0) or 0)
            ready = bool(opportunity.get("destination_ready", False))
            if destination not in by_venue or required <= 0:
                continue

            for source, venue in by_venue.items():
                if source == destination:
                    continue
                if str(venue.get("owner_id", owner_id)) != owner_id:
                    continue

                balances = venue.get("quote_cash", {}) or {}
                available = float(balances.get(asset, 0) or 0)
                baseline = float(
                    (venue.get("baseline_capital_quote", {}) or {}).get(asset, 0) or 0
                )
                if available <= 0 or baseline <= 0:
                    continue

                ok, reason = self.policy.can_route(
                    source_owner_id=owner_id,
                    destination_owner_id=str(by_venue[destination].get("owner_id", owner_id)),
                    source_available_quote=available,
                    source_baseline_capital_quote=baseline,
                    destination_required_quote=required,
                    expected_net_edge_bps=edge,
                    estimated_transfer_cost_quote=transfer_cost,
                    destination_ready=ready,
                )
                if not ok:
                    continue

                surplus = self.policy.transferable_surplus(
                    source_equity_quote=available,
                    source_baseline_capital_quote=baseline,
                )
                amount = min(
                    required,
                    surplus,
                    available * (1 - self.policy.reserve_cash_pct),
                    available * self.policy.max_transfer_pct_per_cycle,
                )
                if amount < self.policy.minimum_transfer_quote:
                    continue

                candidates.append(
                    CapitalRouteCandidate(
                        source_venue=source,
                        destination_venue=destination,
                        asset=asset,
                        amount_quote=amount,
                        expected_net_edge_bps=edge,
                        estimated_transfer_cost_quote=transfer_cost,
                        reason=reason,
                    )
                )
                break

        return sorted(
            candidates,
            key=lambda item: (item.expected_net_edge_bps, item.amount_quote),
            reverse=True,
        )

    @staticmethod
    def snapshot(candidates: list[CapitalRouteCandidate]) -> dict[str, Any]:
        return {
            "execution_authority": "NONE",
            "owner_private": True,
            "candidates": [
                {
                    "source_venue": c.source_venue,
                    "destination_venue": c.destination_venue,
                    "asset": c.asset,
                    "amount_quote": c.amount_quote,
                    "expected_net_edge_bps": c.expected_net_edge_bps,
                    "estimated_transfer_cost_quote": c.estimated_transfer_cost_quote,
                    "reason": c.reason,
                }
                for c in candidates
            ],
        }
