from __future__ import annotations

import json
from pathlib import Path
from dataclasses import dataclass


@dataclass(frozen=True)
class ContextEvidence:
    samples: int
    wins: int
    mean_net_bps: float
    eligible: bool
    source: str


class AdaptiveRiskEvidenceStore:
    """Reads PAPER outcome evidence for adaptive sizing; missing data fails closed."""

    def __init__(self, path: str, *, max_rows: int = 50000) -> None:
        self.path = Path(path)
        self.max_rows = max(100, int(max_rows))

    def lookup(self, *, symbol: str, regime: str | None, horizon_seconds: int | None, action: str = "BUY") -> ContextEvidence | None:
        if not self.path.exists():
            return None
        target_horizon = int(horizon_seconds or 0) * 1000
        rows = []
        try:
            with self.path.open("r", encoding="utf-8") as handle:
                for line in handle:
                    if line.strip():
                        rows.append(json.loads(line))
        except (OSError, ValueError, TypeError):
            return None
        for row in reversed(rows[-self.max_rows:]):
            if str(row.get("symbol", "")).upper() != str(symbol).upper():
                continue
            if str(row.get("action", "")).upper() != str(action).upper():
                continue
            if str(row.get("regime", "UNKNOWN")) != str(regime or "UNKNOWN"):
                continue
            if int(row.get("horizon_ms", 0)) != target_horizon:
                continue
            return ContextEvidence(int(row.get("samples", 0)), int(row.get("wins", 0)), float(row.get("mean_net_bps", 0.0)), bool(row.get("eligible", False)), "state_outcomes")
        return None
