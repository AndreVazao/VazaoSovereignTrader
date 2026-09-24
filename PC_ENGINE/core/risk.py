from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import asdict, dataclass, field

from PC_ENGINE.core.adaptive_risk import AdaptiveRiskController, AdaptiveRiskSnapshot
from PC_ENGINE.core.adaptive_risk_evidence import AdaptiveRiskEvidenceStore


@dataclass(frozen=True)
class RiskDecision:
    authorized: bool
    reason: str

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
        defaults = {
            "max_daily_loss_pct": -0.03,
            "max_weekly_loss_pct": -0.08,
            "kill_cooldown_seconds": 900.0,
            "max_symbol_loss_streak": 3,
            "cooldown_after_loss_seconds": 900.0,
            "risk_per_trade_pct": 0.01,
        }
        self.settings = {**defaults, **(settings or {})}
        self.state = RiskState()
        adaptive_cfg = settings.get("adaptive_risk", {})
        self.adaptive_risk = AdaptiveRiskController(adaptive_cfg)
        self.adaptive_evidence = AdaptiveRiskEvidenceStore(
            str(adaptive_cfg.get("outcome_path", "PC_ENGINE/data/radar/state_outcomes.jsonl"))
        )

    def authorize_signal(self, symbol: str, action: str, now: float | None = None) -> RiskDecision:
        """Final PAPER risk boundary for a proposed BUY/SELL signal."""
        normalized = str(action).upper()
        if normalized not in {"BUY", "SELL"}:
            return RiskDecision(False, "risk engine requires BUY or SELL")
        global_ok, global_reason = self.can_trade_global(now)
        if not global_ok:
            return RiskDecision(False, global_reason)
        symbol_ok, symbol_reason = self.can_trade_symbol(symbol, now)
        if not symbol_ok:
            return RiskDecision(False, symbol_reason)
        return RiskDecision(True, "risk engine authorized")

    def snapshot_state(self) -> dict:
        state = {
            "pnl_today_pct": float(self.state.pnl_today_pct),
            "pnl_week_pct": float(self.state.pnl_week_pct),
            "drawdown_pct": float(self.state.drawdown_pct),
            "equity_peak": float(self.state.equity_peak),
            "kill_until": float(self.state.kill_until),
            "symbol_loss_streak": {str(k): int(v) for k, v in self.state.symbol_loss_streak.items()},
            "symbol_cooldown_until": {str(k): float(v) for k, v in self.state.symbol_cooldown_until.items()},
        }
        state["symbol_cooldown_until"] = {str(k): float(v) for k, v in self.state.symbol_cooldown_until.items()}
        return state

    def restore_state(self, raw: dict) -> None:
        if not isinstance(raw, dict):
            raise ValueError("risk_state must be an object")
        restored = RiskState()
        for name in ("pnl_today_pct", "pnl_week_pct", "drawdown_pct", "equity_peak", "kill_until"):
            setattr(restored, name, float(raw.get(name, getattr(restored, name))))
        streaks = raw.get("symbol_loss_streak", {})
        cooldowns = raw.get("symbol_cooldown_until", {})
        if not isinstance(streaks, dict) or not isinstance(cooldowns, dict):
            raise ValueError("risk_state symbol maps must be objects")
        restored.symbol_loss_streak.update({str(k): int(v) for k, v in streaks.items()})
        restored.symbol_cooldown_until.update({str(k): float(v) for k, v in cooldowns.items()})
        self.state = restored

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
        self, equity: float, stop_pct: float, *, samples: int, wins: int, mean_net_bps: float,
        strategy_id: str = "unknown", symbol: str = "unknown", regime: str | None = None,
        horizon_seconds: int | None = None, lower_ci_bps: float = 0.0, evidence_age_ms: int = 0,
        regime_stability: float = 0.0, independent_samples: int = 0,
        independent_mean_net_bps: float = 0.0,
    ) -> tuple[float, AdaptiveRiskSnapshot]:
        base = self.position_notional(equity, stop_pct)
        context = self.adaptive_risk.context_key(strategy_id=strategy_id, symbol=symbol, regime=regime, horizon_seconds=horizon_seconds)
        snapshot = self.adaptive_risk.evaluate(
            samples=samples, wins=wins, mean_net_bps=mean_net_bps,
            drawdown_pct=max(0.0, -self.state.drawdown_pct), context_key=context,
            lower_ci_bps=lower_ci_bps, evidence_age_ms=evidence_age_ms,
            regime_stability=regime_stability, independent_samples=independent_samples,
            independent_mean_net_bps=independent_mean_net_bps,
        )
        return base * snapshot.multiplier, snapshot

    def record_trade_result(self, symbol: str, pnl_pct: float) -> None:
        self.state.pnl_today_pct += pnl_pct
        self.state.pnl_week_pct += pnl_pct
        if pnl_pct < 0:
            self.state.symbol_loss_streak[symbol] += 1
        else:
            self.state.symbol_loss_streak[symbol] = 0

    def adaptive_position_notional_auto(
        self, equity: float, stop_pct: float, *, strategy_id: str = "unknown",
        symbol: str = "unknown", regime: str | None = None, horizon_seconds: int | None = None,
        action: str = "BUY",
    ) -> tuple[float, AdaptiveRiskSnapshot]:
        evidence = self.adaptive_evidence.lookup(symbol=symbol, regime=regime, horizon_seconds=horizon_seconds, action=action)
        if evidence is None:
            return self.adaptive_position_notional(equity, stop_pct, samples=0, wins=0, mean_net_bps=0.0, strategy_id=strategy_id, symbol=symbol, regime=regime, horizon_seconds=horizon_seconds)
        return self.adaptive_position_notional(
            equity, stop_pct, samples=evidence.samples, wins=evidence.wins, mean_net_bps=evidence.mean_net_bps,
            strategy_id=strategy_id, symbol=symbol, regime=regime, horizon_seconds=horizon_seconds,
            lower_ci_bps=evidence.lower_ci_bps, evidence_age_ms=evidence.evidence_age_ms,
            regime_stability=evidence.regime_stability, independent_samples=evidence.independent_samples,
            independent_mean_net_bps=evidence.independent_mean_net_bps,
        )
