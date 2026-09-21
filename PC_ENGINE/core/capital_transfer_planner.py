from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from PC_ENGINE.core.capital_routing_policy import CapitalRoutingPolicy


@dataclass(frozen=True)
class CapitalRouteCandidate:
    source_venue: str
    destination_venue: str
    asset: str
    network: str
    amount_quote: float
    expected_net_edge_bps: float
    estimated_transfer_cost_quote: float
    estimated_transfer_time_seconds: float
    reason: str


class CapitalTransferPlanner:
    """Owner-private, decision-only planner for venue-to-venue capital routing.

    It never transfers funds. A route is only proposed when the source and
    destination explicitly agree on the asset/network and the route economics
    survive transfer costs, minimums and expected settlement delay.
    """

    def __init__(self, policy: CapitalRoutingPolicy):
        self.policy = policy

    @staticmethod
    def _route_network(
        source: dict[str, Any],
        destination: dict[str, Any],
        opportunity: dict[str, Any],
    ) -> str | None:
        requested = str(opportunity.get("network", "")).upper().strip()
        source_networks = {
            str(item).upper().strip()
            for item in (source.get("transfer_networks", {}) or {}).get(
                str(opportunity.get("asset", "USDT")).upper(), []
            )
        }
        destination_networks = {
            str(item).upper().strip()
            for item in (destination.get("transfer_networks", {}) or {}).get(
                str(opportunity.get("asset", "USDT")).upper(), []
            )
        }
        common = source_networks & destination_networks
        if requested:
            return requested if requested in common else None
        return sorted(common)[0] if common else None

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
            destination_id = str(opportunity.get("destination_venue", "")).lower()
            asset = str(opportunity.get("asset", "USDT")).upper()
            required = float(opportunity.get("required_quote", 0) or 0)
            edge = float(opportunity.get("expected_net_edge_bps", 0) or 0)
            transfer_cost = float(opportunity.get("estimated_transfer_cost_quote", 0) or 0)
            transfer_time = float(opportunity.get("estimated_transfer_time_seconds", 0) or 0)
            ready = bool(opportunity.get("destination_ready", False))
            destination_whitelisted = bool(opportunity.get("destination_whitelisted", False))
            if destination_id not in by_venue or required <= 0:
                continue

            destination = by_venue[destination_id]
            destination_owner = str(destination.get("owner_id", owner_id))
            for source_id, source in by_venue.items():
                if source_id == destination_id:
                    continue
                if str(source.get("owner_id", owner_id)) != owner_id:
                    continue

                network = self._route_network(source, destination, opportunity)
                if network is None:
                    continue

                balances = source.get("quote_cash", {}) or {}
                available = float(balances.get(asset, 0) or 0)
                baseline = float(
                    (source.get("baseline_capital_quote", {}) or {}).get(asset, 0) or 0
                )
                if available <= 0 or baseline <= 0:
                    continue

                ok, reason = self.policy.can_route(
                    source_owner_id=owner_id,
                    destination_owner_id=destination_owner,
                    source_available_quote=available,
                    source_baseline_capital_quote=baseline,
                    destination_required_quote=required,
                    expected_net_edge_bps=edge,
                    estimated_transfer_cost_quote=transfer_cost,
                    destination_ready=ready,
                    destination_whitelisted=destination_whitelisted,
                )
                if not ok:
                    continue

                min_transfer = float(opportunity.get("minimum_transfer_quote", 0) or 0)
                if min_transfer > 0 and required < min_transfer:
                    continue
                max_delay = float(opportunity.get("max_settlement_seconds", 0) or 0)
                if max_delay > 0 and transfer_time > max_delay:
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
                if amount <= transfer_cost:
                    continue

                candidates.append(
                    CapitalRouteCandidate(
                        source_venue=source_id,
                        destination_venue=destination_id,
                        asset=asset,
                        network=network,
                        amount_quote=amount,
                        expected_net_edge_bps=edge,
                        estimated_transfer_cost_quote=transfer_cost,
                        estimated_transfer_time_seconds=transfer_time,
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
                    "network": c.network,
                    "amount_quote": c.amount_quote,
                    "expected_net_edge_bps": c.expected_net_edge_bps,
                    "estimated_transfer_cost_quote": c.estimated_transfer_cost_quote,
                    "estimated_transfer_time_seconds": c.estimated_transfer_time_seconds,
                    "reason": c.reason,
                }
                for c in candidates
            ],
        }
