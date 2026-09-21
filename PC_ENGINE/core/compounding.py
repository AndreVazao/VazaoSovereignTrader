from __future__ import annotations

from dataclasses import dataclass


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


class CompoundingController:
    """Owner-private equity compounding policy.

    Profits remain part of the trading equity by default. Position sizing should
    be calculated from current equity, while the risk multiplier remains bounded
    by validated adaptive-risk evidence. This controller never promises a return
    and never executes transfers.
    """

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

    def snapshot(
        self,
        *,
        baseline_capital: float,
        equity: float,
        adaptive_risk_multiplier: float = 1.0,
    ) -> CompoundingSnapshot:
        baseline = max(0.0, float(baseline_capital))
        current = max(0.0, float(equity))
        if baseline <= 0:
            raise ValueError("baseline_capital must be positive")
        multiplier = max(0.0, float(adaptive_risk_multiplier))
        multiplier = min(multiplier, self.max_equity_multiplier)

        realized_profit = current - baseline
        return_pct = realized_profit / baseline
        protected_reserve = current * self.reserve_cash_pct
        # Equity, rather than the original deposit, is the compounding base.
        # A losing cycle naturally reduces the next position size.
        reinvestment_equity = current
        transferable_surplus = max(0.0, current - baseline)

        status = "COMPOUNDING" if current > 0 else "STOPPED"
        if current < baseline:
            status = "RECOVERY"
        elif realized_profit > 0:
            status = "PROFIT_COMPOUNDING"

        return CompoundingSnapshot(
            owner_id=self.owner_id,
            venue=self.venue,
            baseline_capital=round(baseline, 8),
            equity=round(current, 8),
            realized_profit=round(realized_profit, 8),
            return_pct=round(return_pct, 8),
            reinvestment_equity=round(reinvestment_equity, 8),
            risk_multiplier=round(multiplier, 8),
            transferable_surplus=round(transferable_surplus, 8),
            protected_reserve=round(protected_reserve, 8),
            status=status,
        )

    def next_trade_equity(self, *, current_equity: float, realized_pnl: float) -> float:
        """Return the equity base after a completed trade.

        The result is deliberately simple: realized P&L is compounded into the
        next trade's capital base. Risk controls determine how much of that
        equity may actually be exposed.
        """
        equity = max(0.0, float(current_equity))
        pnl = float(realized_pnl)
        return round(max(0.0, equity + pnl), 8)
