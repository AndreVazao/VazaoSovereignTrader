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


class AdaptiveRiskController:
    """PAPER-first adaptive risk policy.

    Risk can increase only when independent evidence supports it.
    Win rate alone is never sufficient: minimum samples, positive
    expectancy, drawdown and a hard multiplier ceiling all apply.
    """

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

    def evaluate(
        self,
        *,
        samples: int,
        wins: int,
        mean_net_bps: float,
        drawdown_pct: float,
    ) -> AdaptiveRiskSnapshot:
        samples = max(0, int(samples))
        wins = min(max(0, int(wins)), samples)
        win_rate = wins / samples if samples else 0.0
        dd = max(0.0, float(drawdown_pct))

        if not self.enabled:
            return AdaptiveRiskSnapshot(samples, wins, win_rate, float(mean_net_bps), dd,
                                        self.base_multiplier, False, "adaptive risk disabled")
        if samples < self.min_samples:
            return AdaptiveRiskSnapshot(samples, wins, win_rate, float(mean_net_bps), dd,
                                        self.min_multiplier, False, "insufficient validated samples")
        if dd >= self.max_drawdown_pct:
            return AdaptiveRiskSnapshot(samples, wins, win_rate, float(mean_net_bps), dd,
                                        self.min_multiplier, False, "drawdown protection active")
        if win_rate < self.min_win_rate:
            return AdaptiveRiskSnapshot(samples, wins, win_rate, float(mean_net_bps), dd,
                                        self.min_multiplier, False, "win rate below threshold")
        if float(mean_net_bps) <= self.min_mean_net_bps:
            return AdaptiveRiskSnapshot(samples, wins, win_rate, float(mean_net_bps), dd,
                                        self.min_multiplier, False, "net expectancy below threshold")

        # Scale gradually with evidence quality; never jump directly to the ceiling.
        evidence = min(1.0, samples / self.scale_window)
        quality = min(1.0, max(0.0, (win_rate - self.min_win_rate) / max(1e-9, 1.0 - self.min_win_rate)))
        expectancy = min(1.0, max(0.0, float(mean_net_bps) / max(1e-9, self.min_mean_net_bps * 3.0)))
        confidence = evidence * (0.5 * quality + 0.5 * expectancy)
        multiplier = self.base_multiplier + (self.max_multiplier - self.base_multiplier) * confidence
        multiplier = min(self.max_multiplier, max(self.base_multiplier, multiplier))

        return AdaptiveRiskSnapshot(samples, wins, win_rate, float(mean_net_bps), dd,
                                    multiplier, True, "validated positive edge")
