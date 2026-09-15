from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class PaperLeadLagSignal:
    symbol: str
    leader: str
    follower: str
    direction: str
    horizon_ms: int
    expectancy_bps: float
    confidence: float
    samples: int
    regime: str = "UNKNOWN"
    paper_only: bool = True


class LeadLagSignalEngine:
    """Turns learned statistics into descriptive PAPER signals only."""

    def __init__(self, data_dir: str | Path = "PC_ENGINE/data/radar") -> None:
        self.data_dir = Path(data_dir)

    def load(self) -> list[dict[str, Any]]:
        path = self.data_dir / "lead_lag_learning.json"
        if not path.exists():
            return []
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            rows = payload.get("stats", [])
            return [row for row in rows if isinstance(row, dict)]
        except (OSError, json.JSONDecodeError):
            return []

    def signals(self, min_confidence: float = 0.75) -> list[PaperLeadLagSignal]:
        result: list[PaperLeadLagSignal] = []
        for row in self.load():
            if not row.get("eligible"):
                continue
            confidence = float(row.get("confidence", 0.0))
            if confidence < min_confidence:
                continue
            result.append(PaperLeadLagSignal(
                symbol=str(row["symbol"]),
                leader=str(row["leader"]),
                follower=str(row["follower"]),
                direction=str(row["direction"]),
                horizon_ms=int(row["horizon_ms"]),
                expectancy_bps=float(row["expectancy_bps"]),
                confidence=confidence,
                samples=int(row["samples"]),
                paper_only=True,
            ))
        result.sort(key=lambda x: (x.expectancy_bps, x.confidence, x.samples), reverse=True)
        return result
