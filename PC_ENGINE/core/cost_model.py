from __future__ import annotations

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class CostBreakdown:
    """Execution-cost estimate expressed in basis points.

    All inputs are non-negative bps. The model is deliberately conservative:
    every cost component is additive and the opportunity gate is fail-closed
    when required values are invalid.
    """

    fee_bps: float
    spread_bps: float
    slippage_bps: float
    liquidity_bps: float
    latency_bps: float
    total_bps: float
    gross_edge_bps: float
    net_edge_bps: float
    viable: bool
    reason: str


class OpportunityCostGate:
    """Converts a gross expected edge into a cost-aware PAPER opportunity gate."""

    def __init__(
        self,
        *,
        minimum_net_edge_bps: float = 2.0,
        minimum_edge_margin_bps: float = 1.0,
        max_total_cost_bps: float = 100.0,
    ) -> None:
        self.minimum_net_edge_bps = max(0.0, float(minimum_net_edge_bps))
        self.minimum_edge_margin_bps = max(0.0, float(minimum_edge_margin_bps))
        self.max_total_cost_bps = max(0.0, float(max_total_cost_bps))

    @staticmethod
    def _bps(value: float, name: str) -> float:
        try:
            value = float(value)
        except (TypeError, ValueError):
            raise ValueError(f"{name} must be numeric")
        if not math.isfinite(value) or value < 0:
            raise ValueError(f"{name} must be finite and non-negative")
        return value

    def evaluate(
        self,
        *,
        gross_edge_bps: float,
        fee_bps: float = 0.0,
        spread_bps: float = 0.0,
        slippage_bps: float = 0.0,
        liquidity_bps: float = 0.0,
        latency_bps: float = 0.0,
    ) -> CostBreakdown:
        gross = self._bps(gross_edge_bps, "gross_edge_bps")
        fee = self._bps(fee_bps, "fee_bps")
        spread = self._bps(spread_bps, "spread_bps")
        slippage = self._bps(slippage_bps, "slippage_bps")
        liquidity = self._bps(liquidity_bps, "liquidity_bps")
        latency = self._bps(latency_bps, "latency_bps")

        total = fee + spread + slippage + liquidity + latency
        net = gross - total
        margin = net - self.minimum_net_edge_bps

        if total > self.max_total_cost_bps:
            return CostBreakdown(
                fee, spread, slippage, liquidity, latency, total, gross, net,
                False, "costs exceed configured maximum",
            )
        if net < self.minimum_net_edge_bps:
            return CostBreakdown(
                fee, spread, slippage, liquidity, latency, total, gross, net,
                False, "net edge below minimum",
            )
        if margin < self.minimum_edge_margin_bps:
            return CostBreakdown(
                fee, spread, slippage, liquidity, latency, total, gross, net,
                False, "edge margin below minimum",
            )

        return CostBreakdown(
            fee, spread, slippage, liquidity, latency, total, gross, net,
            True, "cost-adjusted edge is viable",
        )
