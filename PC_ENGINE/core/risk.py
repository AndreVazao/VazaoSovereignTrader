from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field

from PC_ENGINE.core.adaptive_risk import AdaptiveRiskController, AdaptiveRiskSnapshot


@dataclass
class RiskState:
    pnl_today_pct: float = 0.0
    pnl_week_pct: float = 0.0
    drawdown_pct: float = 0.0
    equity_peak: float = 0.0
    kill_until: float = 0.0
    symbol_loss_streak: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    symbol_cooldown_until: dict[str, float] = field(default_factory=dict)


class RiskEngine:
    def __init__(self, settings: dict):
        self.settings = settings
        self.state = RiskState()
        self.adaptive_risk = AdaptiveRiskController(settings.get("adaptive_risk", {}))

    def update_equity(self, equity: float, starting_equity: float) -> None:
        if self.state.equity_peak <= 0:
            self.state.equity_peak = max(equity, starting_equity)
        self.state.equity_peak = max(self.state.equity_peak, equity)
        if self.state.equity_peak > 0:
            self.state.drawdown_pct = (equity - self.state.equity_peak) / self.state.equity_peak

    def can_trade_global(self, now: float | None = None) -> tuple[bool, str]:
        now = now or time.time()
        if now < self.state.kill_until:
            return False, "global kill cooldown active"
        if self.state.pnl_today_pct <= float(self.settings["max_daily_loss_pct"]):
            self.state.kill_until = now + float(self.settings["kill_cooldown_seconds"])
            return False, "daily drawdown limit reached"
        if self.state.pnl_week_pct <= float(self.settings["max_weekly_loss_pct"]):
            self.state.kill_until = now + float(self.settings["kill_cooldown_seconds"])
            return False, "weekly drawdown limit reached"
        return True, "ok"

    def can_trade_symbol(self, symbol: str, now: float | None = None) -> tuple[bool, str]:
        now = now or time.time()
        until = self.state.symbol_cooldown_until.get(symbol, 0.0)
        if now < until:
            return False, f"{symbol} cooldown active"
        if self.state.symbol_loss_streak.get(symbol, 0) >= int(self.settings["max_symbol_loss_streak"]):
            self.state.symbol_cooldown_until[symbol] = now + float(self.settings["cooldown_after_loss_seconds"])
            self.state.symbol_loss_streak[symbol] = 0
            return False, f"{symbol} loss streak cooldown"
        return True, "ok"

    def position_notional(self, equity: float, stop_pct: float) -> float:
        if stop_pct <= 0 or equity <= 0:
            return 0.0
        risk_amount = equity * float(self.settings["risk_per_trade_pct"])
        return max(0.0, risk_amount / stop_pct)

    def adaptive_position_notional(
        self,
        equity: float,
        stop_pct: float,
        *,
        samples: int,
        wins: int,
        mean_net_bps: float,
        strategy_id: str = "unknown",
        symbol: str = "unknown",
        regime: str | None = None,
        horizon_seconds: int | None = None,
    ) -> tuple[float, AdaptiveRiskSnapshot]:
        base = self.position_notional(equity, stop_pct)
        context = self.adaptive_risk.context_key(strategy_id=strategy_id, symbol=symbol, regime=regime, horizon_seconds=horizon_seconds)
        snapshot = self.adaptive_risk.evaluate(
            samples=samples,
            wins=wins,
            mean_net_bps=mean_net_bps,
            drawdown_pct=max(0.0, -self.state.drawdown_pct),
            context_key=context,
        )
        return base * snapshot.multiplier, snapshot

    def record_trade_result(self, symbol: str, pnl_pct: float) -> None:
        self.state.pnl_today_pct += pnl_pct
        self.state.pnl_week_pct += pnl_pct
        if pnl_pct < 0:
            self.state.symbol_loss_streak[symbol] += 1
        else:
            self.state.symbol_loss_streak[symbol] = 0
