from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CompoundingSnapshot:
    owner_id: str
    venue: str
    baseline_capital: float
    equity: float
    realized_profit: float
    return_pct: float
    reinvestment_equity: float
    risk_multiplier: float
    transferable_surplus: float
    protected_reserve: float
    status: str


@dataclass(frozen=True)
class VenueCompoundingStatus:
    venue: str
    equity: float
    target_base: float
    surplus: float
    funding_need: float
    at_target: bool


@dataclass(frozen=True)
class GlobalCompoundingSnapshot:
    owner_id: str
    seed_base: float
    growth_factor: float
    global_base: float
    next_base: float
    total_equity: float
    all_venues_at_base: bool
    venues: tuple[VenueCompoundingStatus, ...]


class CompoundingController:
    """Owner-private equity compounding policy."""

    def __init__(
        self,
        *,
        owner_id: str,
        venue: str,
        reserve_cash_pct: float = 0.20,
        max_equity_multiplier: float = 10_000.0,
    ):
        self.owner_id = str(owner_id or "").strip().lower()
        self.venue = str(venue or "").strip().lower()
        self.reserve_cash_pct = float(reserve_cash_pct)
        self.max_equity_multiplier = max(1.0, float(max_equity_multiplier))
        if not self.owner_id:
            raise ValueError("owner_id is required")
        if not self.venue:
            raise ValueError("venue is required")
        if not 0 <= self.reserve_cash_pct < 1:
            raise ValueError("reserve_cash_pct must be in [0, 1)")

    def snapshot(self, *, baseline_capital: float, equity: float, adaptive_risk_multiplier: float = 1.0) -> CompoundingSnapshot:
        baseline = max(0.0, float(baseline_capital))
        current = max(0.0, float(equity))
        if baseline <= 0:
            raise ValueError("baseline_capital must be positive")
        multiplier = min(max(0.0, float(adaptive_risk_multiplier)), self.max_equity_multiplier)
        realized_profit = current - baseline
        return_pct = realized_profit / baseline
        protected_reserve = current * self.reserve_cash_pct
        reinvestment_equity = current
        transferable_surplus = max(0.0, current - baseline)
        status = "COMPOUNDING" if current > 0 else "STOPPED"
        if current < baseline:
            status = "RECOVERY"
        elif realized_profit > 0:
            status = "PROFIT_COMPOUNDING"
        return CompoundingSnapshot(
            owner_id=self.owner_id, venue=self.venue,
            baseline_capital=round(baseline, 8), equity=round(current, 8),
            realized_profit=round(realized_profit, 8), return_pct=round(return_pct, 8),
            reinvestment_equity=round(reinvestment_equity, 8),
            risk_multiplier=round(multiplier, 8),
            transferable_surplus=round(transferable_surplus, 8),
            protected_reserve=round(protected_reserve, 8), status=status,
        )

    def tier_for_equity(self, *, total_equity: float, seed_capital: float = 1.0, growth_factor: float = 10.0) -> float:
        equity = max(0.0, float(total_equity))
        tier = float(seed_capital)
        factor = float(growth_factor)
        if tier <= 0 or factor <= 1:
            raise ValueError("seed_capital must be positive and growth_factor > 1")
        while equity >= tier * factor:
            tier *= factor
        return round(tier, 8)

    def next_global_base(self, *, total_equity: float, current_base: float, growth_factor: float = 10.0) -> float:
        equity = max(0.0, float(total_equity))
        base = float(current_base)
        factor = float(growth_factor)
        if base <= 0 or factor <= 1:
            raise ValueError("current_base must be positive and growth_factor > 1")
        while equity >= base * factor:
            base *= factor
        return round(base, 8)

    def next_trade_equity(self, *, current_equity: float, realized_pnl: float) -> float:
        return round(max(0.0, max(0.0, float(current_equity)) + float(realized_pnl)), 8)


class GlobalCompoundingOrchestrator:
    """Coordinate the owner-private global 10x capitalization ladder.

    The base advances only when every configured active venue reaches it.
    This plans targets and surplus/deficit relationships; it never executes
    transfers or bypasses risk, venue, network, settlement, or routing gates.
    """

    def __init__(self, *, owner_id: str, venues: list[str], seed_base: float = 1.0, growth_factor: float = 10.0):
        self.owner_id = str(owner_id or "").strip().lower()
        self.venues = tuple(dict.fromkeys(str(v).strip().lower() for v in venues if str(v).strip()))
        self.seed_base = float(seed_base)
        self.growth_factor = float(growth_factor)
        if not self.owner_id or not self.venues:
            raise ValueError("owner_id and at least one venue are required")
        if self.seed_base <= 0 or self.growth_factor <= 1:
            raise ValueError("seed_base must be positive and growth_factor > 1")

    def current_base(self, equities: dict[str, float]) -> float:
        normalized = {str(k).strip().lower(): max(0.0, float(v)) for k, v in equities.items()}
        minimum_equity = min((normalized.get(v, 0.0) for v in self.venues), default=0.0)
        controller = CompoundingController(owner_id=self.owner_id, venue="global")
        return controller.tier_for_equity(
            total_equity=minimum_equity, seed_capital=self.seed_base, growth_factor=self.growth_factor
        )

    def snapshot(self, equities: dict[str, float]) -> GlobalCompoundingSnapshot:
        normalized = {str(k).strip().lower(): max(0.0, float(v)) for k, v in equities.items()}
        total = sum(normalized.get(v, 0.0) for v in self.venues)
        base = self.current_base(normalized)
        statuses = tuple(
            VenueCompoundingStatus(
                venue=venue, equity=round(normalized.get(venue, 0.0), 8),
                target_base=round(base, 8),
                surplus=round(max(0.0, normalized.get(venue, 0.0) - base), 8),
                funding_need=round(max(0.0, base - normalized.get(venue, 0.0)), 8),
                at_target=normalized.get(venue, 0.0) >= base,
            )
            for venue in self.venues
        )
        all_at_base = all(item.at_target for item in statuses)
        return GlobalCompoundingSnapshot(
            owner_id=self.owner_id, seed_base=self.seed_base, growth_factor=self.growth_factor,
            global_base=round(base, 8),
            next_base=round(base * self.growth_factor if all_at_base else base, 8),
            total_equity=round(total, 8), all_venues_at_base=all_at_base, venues=statuses,
        )

    def funding_plan(self, equities: dict[str, float]) -> list[dict[str, Any]]:
        snap = self.snapshot(equities)
        sources = [v for v in snap.venues if v.surplus > 0]
        destinations = [v for v in snap.venues if v.funding_need > 0]
        plan: list[dict[str, Any]] = []
        for destination in sorted(destinations, key=lambda x: x.funding_need, reverse=True):
            remaining = destination.funding_need
            for source in sorted(sources, key=lambda x: x.surplus, reverse=True):
                if remaining <= 0 or source.surplus <= 0 or source.venue == destination.venue:
                    continue
                amount = min(source.surplus, remaining)
                if amount <= 0:
                    continue
                plan.append({
                    "owner_id": snap.owner_id,
                    "source_venue": source.venue,
                    "destination_venue": destination.venue,
                    "target_base": target_base,
                    "amount": round(amount, 8),
                    "reason": "GLOBAL_TIER_CAPITALIZATION",
                })
                remaining -= amount
        return plan
