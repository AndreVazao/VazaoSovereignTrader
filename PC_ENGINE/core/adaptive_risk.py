from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AdaptiveRiskSnapshot:
    samples: int
    wins: int
    win_rate: float
    mean_net_bps: float
    drawdown_pct: float
    multiplier: float
    eligible: bool
    reason: str
    context_key: str = "global"
    lower_ci_bps: float = 0.0
    evidence_age_ms: int = 0
    regime_stability: float = 0.0


class AdaptiveRiskController:
    """PAPER-first adaptive risk policy using statistically confirmed, fresh evidence."""

    def __init__(self, settings: dict):
        cfg = dict(settings or {})
        self.enabled = bool(cfg.get("enabled", True))
        self.min_samples = max(1, int(cfg.get("min_samples", 100)))
        self.min_win_rate = float(cfg.get("min_win_rate", 0.55))
        self.min_mean_net_bps = float(cfg.get("min_mean_net_bps", 2.0))
        self.max_drawdown_pct = abs(float(cfg.get("max_drawdown_pct", 0.02)))
        self.base_multiplier = max(0.0, float(cfg.get("base_multiplier", 1.0)))
        self.max_multiplier = max(self.base_multiplier, float(cfg.get("max_multiplier", 1.5)))
        self.min_multiplier = min(self.base_multiplier, max(0.0, float(cfg.get("min_multiplier", 0.5))))
        self.scale_window = max(1, int(cfg.get("scale_window", 400)))
        self.max_evidence_age_ms = max(1, int(cfg.get("max_evidence_age_ms", 86_400_000)))
        self.min_regime_stability = max(0.0, min(1.0, float(cfg.get("min_regime_stability", 0.60))))

    def evaluate(
        self, *, samples: int, wins: int, mean_net_bps: float, drawdown_pct: float,
        context_key: str = "global", lower_ci_bps: float = 0.0,
        evidence_age_ms: int = 0, regime_stability: float = 0.0,
        independent_samples: int = 0, independent_mean_net_bps: float = 0.0,
    ) -> AdaptiveRiskSnapshot:
        samples = max(0, int(samples))
        wins = min(max(0, int(wins)), samples)
        win_rate = wins / samples if samples else 0.0
        dd = max(0.0, float(drawdown_pct))
        context_key = str(context_key or "global")[:256]
        lower_ci_bps = float(lower_ci_bps)
        evidence_age_ms = max(0, int(evidence_age_ms))
        regime_stability = max(0.0, min(1.0, float(regime_stability)))
        independent_samples = max(0, int(independent_samples))

        def blocked(reason: str) -> AdaptiveRiskSnapshot:
            return AdaptiveRiskSnapshot(
                samples, wins, win_rate, float(mean_net_bps), dd, self.min_multiplier,
                False, reason, context_key, lower_ci_bps, evidence_age_ms, regime_stability,
            )

        if not self.enabled:
            return AdaptiveRiskSnapshot(
                samples, wins, win_rate, float(mean_net_bps), dd, self.base_multiplier,
                False, "adaptive risk disabled", context_key, lower_ci_bps, evidence_age_ms, regime_stability,
            )
        if samples < self.min_samples:
            return blocked("insufficient contextual evidence")
        if dd >= self.max_drawdown_pct:
            return blocked("drawdown protection active")
        if win_rate < self.min_win_rate:
            return blocked("context win rate below threshold")
        if float(mean_net_bps) <= self.min_mean_net_bps:
            return blocked("context net expectancy below threshold")
        if lower_ci_bps <= 0.0:
            return blocked("confidence interval does not confirm edge")
        if evidence_age_ms > self.max_evidence_age_ms:
            return blocked("evidence is stale")
        if regime_stability < self.min_regime_stability:
            return blocked("regime stability too low")
        if independent_samples >= self.min_samples and independent_mean_net_bps <= 0.0:
            return blocked("independent evidence disagrees")

        evidence = min(1.0, samples / self.scale_window)
        quality = min(1.0, max(0.0, (win_rate - self.min_win_rate) / max(1e-9, 1.0 - self.min_win_rate)))
        expectancy = min(1.0, max(0.0, float(mean_net_bps) / max(1e-9, self.min_mean_net_bps * 3.0)))
        confidence = evidence * (0.4 * quality + 0.4 * expectancy + 0.2 * regime_stability)
        multiplier = self.base_multiplier + (self.max_multiplier - self.base_multiplier) * confidence
        multiplier = min(self.max_multiplier, max(self.base_multiplier, multiplier))
        return AdaptiveRiskSnapshot(
            samples, wins, win_rate, float(mean_net_bps), dd, multiplier, True,
            "validated positive edge with statistical, fresh and regime confirmation",
            context_key, lower_ci_bps, evidence_age_ms, regime_stability,
        )

    def context_key(self, *, strategy_id: str, symbol: str, regime: str | None = None, horizon_seconds: int | None = None) -> str:
        return "|".join([
            str(strategy_id or "unknown").strip().lower(),
            str(symbol or "unknown").strip().upper(),
            str(regime or "unknown").strip().lower(),
            str(horizon_seconds if horizon_seconds is not None else "unknown"),
        ])
