from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ContextEvidence:
    samples: int
    wins: int
    mean_net_bps: float
    lower_ci_bps: float
    eligible: bool
    evidence_age_ms: int
    regime_stability: float
    independent_samples: int = 0
    independent_mean_net_bps: float = 0.0
    source: str = "state_outcomes"


class AdaptiveRiskEvidenceStore:
    """Loads bounded PAPER evidence and exposes quality-aware statistics."""

    def __init__(self, path: str, *, max_rows: int = 50000) -> None:
        self.path = Path(path)
        self.max_rows = max(100, int(max_rows))

    def lookup(self, *, symbol: str, regime: str | None, horizon_seconds: int | None, action: str = "BUY") -> ContextEvidence | None:
        if not self.path.exists():
            return None
        target_horizon = int(horizon_seconds or 0) * 1000
        matches = []
        try:
            with self.path.open("r", encoding="utf-8") as handle:
                for line in handle:
                    if not line.strip():
                        continue
                    row = json.loads(line)
                    if str(row.get("symbol", "")).upper() != str(symbol).upper():
                        continue
                    if str(row.get("action", "")).upper() != str(action).upper():
                        continue
                    if str(row.get("regime", "UNKNOWN")) != str(regime or "UNKNOWN"):
                        continue
                    if int(row.get("horizon_ms", 0)) != target_horizon:
                        continue
                    matches.append(row)
                    if len(matches) > self.max_rows:
                        matches.pop(0)
        except (OSError, ValueError, TypeError):
            return None
        if not matches:
            return None

        row = matches[-1]
        now_ms = int(time.time() * 1000)
        observed_at_ms = int(row.get("observed_at_ms", 0) or 0)
        if observed_at_ms <= 0:
            try:
                observed_at_ms = int(self.path.stat().st_mtime * 1000)
            except OSError:
                return None
        age_ms = max(0, now_ms - observed_at_ms)

        samples = max(0, int(row.get("samples", 0)))
        wins = min(samples, max(0, int(row.get("wins", 0))))
        mean = float(row.get("mean_net_bps", 0.0))
        lower_ci = float(row.get("lower_ci_bps", 0.0))
        eligible = bool(row.get("eligible", False))

        stability = 1.0 if eligible and lower_ci > 0 else 0.0
        if len(matches) >= 2:
            previous = matches[-2]
            previous_mean = float(previous.get("mean_net_bps", 0.0))
            scale = max(1.0, abs(mean), abs(previous_mean))
            stability = max(0.0, min(1.0, 1.0 - abs(mean - previous_mean) / scale))

        return ContextEvidence(
            samples, wins, mean, lower_ci, eligible, age_ms, stability,
            source="state_outcomes",
        )
