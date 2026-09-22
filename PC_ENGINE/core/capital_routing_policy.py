from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CapitalRoutingPolicy:
    """Owner-private policy for moving capital between an owner's own venues.

    Inter-owner transfers are never routable by this policy. A venue only becomes
    a source of automatically transferable capital after its equity has exceeded
    its owner-defined capital baseline by the configured profit threshold.
    """

    owner_id: str
    enabled: bool = True
    reserve_cash_pct: float = 0.20
    minimum_transfer_quote: float = 10.0
    capital_plus_profit_pct: float = 0.0
    max_transfer_pct_per_cycle: float = 0.10
    require_destination_need: bool = True
    require_expected_opportunity: bool = True
    require_destination_ready: bool = True
    require_profit_after_costs: bool = True
    allow_cross_owner_transfer: bool = False
    automatic_same_owner_transfer: bool = True
    require_destination_whitelist: bool = True

    def validate(self) -> None:
        if not self.owner_id:
            raise ValueError("owner_id is required")
        if not 0 <= self.reserve_cash_pct < 1:
            raise ValueError("reserve_cash_pct must be in [0, 1)")
        if self.minimum_transfer_quote < 0:
            raise ValueError("minimum_transfer_quote must be non-negative")
        if self.capital_plus_profit_pct < 0:
            raise ValueError("capital_plus_profit_pct must be non-negative")
        if not 0 < self.max_transfer_pct_per_cycle <= 1:
            raise ValueError("max_transfer_pct_per_cycle must be in (0, 1]")
        if self.allow_cross_owner_transfer:
            raise ValueError("cross-owner transfers are forbidden")
        if self.require_destination_whitelist is False and self.automatic_same_owner_transfer:
            raise ValueError("automatic transfers require destination whitelist")

    def transferable_surplus(
        self,
        *,
        source_equity_quote: float,
        source_baseline_capital_quote: float,
    ) -> float:
        """Return equity above capital + configured profit threshold.

        The baseline is owner-private and must come from the venue's durable
        capital ledger; it is never inferred from another owner's state.
        """
        self.validate()
        if source_equity_quote <= 0 or source_baseline_capital_quote <= 0:
            return 0.0
        threshold = source_baseline_capital_quote * (1 + self.capital_plus_profit_pct)
        return max(0.0, source_equity_quote - threshold)

    def can_route(
        self,
        *,
        source_owner_id: str,
        destination_owner_id: str,
        source_available_quote: float,
        source_baseline_capital_quote: float,
        destination_required_quote: float,
        expected_net_edge_bps: float,
        estimated_transfer_cost_quote: float,
        destination_ready: bool,
        destination_whitelisted: bool = False,
    ) -> tuple[bool, str]:
        self.validate()

        if source_owner_id != self.owner_id or destination_owner_id != self.owner_id:
            return False, "OWNER_BOUNDARY"

        if not self.enabled:
            return False, "ROUTING_DISABLED"
        if not self.automatic_same_owner_transfer:
            return False, "AUTO_TRANSFER_DISABLED"
        if source_available_quote <= 0 or destination_required_quote <= 0:
            return False, "NO_CAPITAL_OR_NEED"

        surplus = self.transferable_surplus(
            source_equity_quote=source_available_quote,
            source_baseline_capital_quote=source_baseline_capital_quote,
        )
        if surplus <= 0:
            return False, "PROFIT_THRESHOLD_NOT_REACHED"

        protected_reserve = source_available_quote * self.reserve_cash_pct
        transferable = min(
            surplus,
            source_available_quote * (1 - self.reserve_cash_pct),
            source_available_quote * self.max_transfer_pct_per_cycle,
        )
        if self.require_destination_need and destination_required_quote > transferable:
            return False, "INSUFFICIENT_SURPLUS"

        if self.require_expected_opportunity and expected_net_edge_bps <= 0:
            return False, "NO_POSITIVE_NET_EDGE"

        if self.require_destination_ready and not destination_ready:
            return False, "DESTINATION_NOT_READY"

        if self.require_profit_after_costs and expected_net_edge_bps <= 0:
            return False, "COSTS_EXCEED_EDGE"

        amount = min(destination_required_quote, transferable)
        if amount < self.minimum_transfer_quote:
            return False, "BELOW_MINIMUM_TRANSFER"

        if amount <= estimated_transfer_cost_quote:
            return False, "TRANSFER_COST_TOO_HIGH"

        if self.require_destination_whitelist and not destination_whitelisted:
            return False, "DESTINATION_NOT_WHITELISTED"

        return True, "ELIGIBLE"

    def snapshot(self) -> dict[str, Any]:
        return {
            "owner_id": self.owner_id,
            "enabled": self.enabled,
            "reserve_cash_pct": self.reserve_cash_pct,
            "minimum_transfer_quote": self.minimum_transfer_quote,
            "capital_plus_profit_pct": self.capital_plus_profit_pct,
            "max_transfer_pct_per_cycle": self.max_transfer_pct_per_cycle,
            "require_destination_need": self.require_destination_need,
            "require_expected_opportunity": self.require_expected_opportunity,
            "require_destination_ready": self.require_destination_ready,
            "require_profit_after_costs": self.require_profit_after_costs,
            "allow_cross_owner_transfer": False,
            "automatic_same_owner_transfer": self.automatic_same_owner_transfer,
            "require_destination_whitelist": self.require_destination_whitelist,
            "execution_authority": "AUTO_SAME_OWNER",
        }
