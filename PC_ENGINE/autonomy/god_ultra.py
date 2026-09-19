from __future__ import annotations

from dataclasses import dataclass, field
from time import monotonic_ns
from typing import Iterable, List, Optional


@dataclass(frozen=True)
class Opportunity:
    opportunity_id: str
    venue: str
    symbol: str
    side: str
    expected_edge_bps: float
    confidence: float
    signal_age_ms: float
    required_capital: float
    liquidity_capital: float
    venue_healthy: bool = True
    clock_healthy: bool = True
    validated: bool = False
    out_of_sample: bool = False
    independent_group: str = "default"
    metadata: dict = field(default_factory=dict)


@dataclass(frozen=True)
class RiskSnapshot:
    available_capital: float
    current_exposure: float = 0.0
    max_exposure: float = 0.0
    daily_loss_pct: float = 0.0
    max_daily_loss_pct: float = -0.02
    kill_switch: bool = False


@dataclass(frozen=True)
class ExecutionIntent:
    opportunity_id: str
    venue: str
    symbol: str
    side: str
    capital: float
    expected_edge_bps: float
    created_ns: int
    execution_group: str


class GodUltraEngine:
    """Fast-path opportunity selector.

    This layer deliberately produces execution intents, not exchange orders.
    A real executor must consume the intents only after the project's existing
    Risk Engine and Real Mode Guard approve the operation.
    """

    def __init__(
        self,
        *,
        min_confidence: float = 0.75,
        min_expectancy_bps: float = 2.0,
        max_signal_age_ms: float = 250.0,
        max_parallel_orders: int = 4,
        reserve_cash_pct: float = 0.20,
        max_single_opportunity_pct: float = 0.10,
    ) -> None:
        self.min_confidence = min_confidence
        self.min_expectancy_bps = min_expectancy_bps
        self.max_signal_age_ms = max_signal_age_ms
        self.max_parallel_orders = max_parallel_orders
        self.reserve_cash_pct = reserve_cash_pct
        self.max_single_opportunity_pct = max_single_opportunity_pct

    def eligible(self, opportunity: Opportunity) -> bool:
        return (
            opportunity.expected_edge_bps >= self.min_expectancy_bps
            and opportunity.confidence >= self.min_confidence
            and opportunity.signal_age_ms <= self.max_signal_age_ms
            and opportunity.venue_healthy
            and opportunity.clock_healthy
            and opportunity.validated
            and opportunity.out_of_sample
            and opportunity.required_capital > 0
            and opportunity.liquidity_capital > 0
        )

    def select(self, opportunities: Iterable[Opportunity], risk: RiskSnapshot) -> List[ExecutionIntent]:
        if risk.kill_switch or risk.available_capital <= 0:
            return []
        if risk.max_exposure > 0 and risk.current_exposure >= risk.max_exposure:
            return []
        if risk.daily_loss_pct <= risk.max_daily_loss_pct:
            return []

        eligible = [o for o in opportunities if self.eligible(o)]
        # Highest expected edge per unit of capital first, while keeping the
        # execution set diversified across independent opportunity groups.
        eligible.sort(
            key=lambda o: (o.expected_edge_bps / max(o.required_capital, 1e-9), o.confidence),
            reverse=True,
        )

        deployable = risk.available_capital * max(0.0, 1.0 - self.reserve_cash_pct)
        if risk.max_exposure > 0:
            deployable = min(deployable, max(0.0, risk.max_exposure - risk.current_exposure))
        max_single = risk.available_capital * self.max_single_opportunity_pct

        selected: List[ExecutionIntent] = []
        used_groups = set()
        used_capital = 0.0
        now = monotonic_ns()

        for opportunity in eligible:
            if len(selected) >= self.max_parallel_orders:
                break
            if opportunity.independent_group in used_groups:
                continue
            capital = min(opportunity.required_capital, opportunity.liquidity_capital, max_single)
            if capital <= 0 or used_capital + capital > deployable:
                continue
            selected.append(
                ExecutionIntent(
                    opportunity_id=opportunity.opportunity_id,
                    venue=opportunity.venue,
                    symbol=opportunity.symbol,
                    side=opportunity.side,
                    capital=capital,
                    expected_edge_bps=opportunity.expected_edge_bps,
                    created_ns=now,
                    execution_group=f"GOD-{now}",
                )
            )
            used_groups.add(opportunity.independent_group)
            used_capital += capital

        return selected
