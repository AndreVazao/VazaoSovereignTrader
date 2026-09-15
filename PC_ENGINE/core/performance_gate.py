from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class PerformanceGateResult:
    status: str
    eligible: bool
    samples: int
    mean_net_bps: float
    win_rate: float
    lower_ci_bps: float
    reason: str


class PerformanceGate:
    """PAPER-only statistical gate for learned confluence performance.

    The gate stays in LEARNING mode until enough completed observations exist.
    This avoids a cold-start deadlock while still preventing an unvalidated
    strategy from becoming REAL execution logic.
    """

    def __init__(
        self,
        data_dir: str | Path = "PC_ENGINE/data/radar",
        min_samples: int = 100,
        min_win_rate: float = 0.52,
        min_mean_net_bps: float = 0.0,
        confidence_z: float = 1.96,
        enforce: bool = True,
    ) -> None:
        self.data_dir = Path(data_dir)
        self.outcome_path = self.data_dir / "confluence_outcomes.jsonl"
        self.min_samples = max(1, int(min_samples))
        self.min_win_rate = float(min_win_rate)
        self.min_mean_net_bps = float(min_mean_net_bps)
        self.confidence_z = float(confidence_z)
        self.enforce = bool(enforce)

    def _read(self) -> list[dict[str, Any]]:
        if not self.outcome_path.exists():
            return []
        rows: list[dict[str, Any]] = []
        for line in self.outcome_path.read_text(encoding="utf-8").splitlines():
            try:
                row = json.loads(line)
                if isinstance(row, dict):
                    rows.append(row)
            except json.JSONDecodeError:
                continue
        return rows

    def evaluate(self, symbol: str, action: str, horizon_ms: int) -> PerformanceGateResult:
        if action not in {"BUY", "SELL"}:
            return PerformanceGateResult("NOT_APPLICABLE", True, 0, 0.0, 0.0, 0.0, "action is not directional")

        rows = [
            row for row in self._read()
            if str(row.get("symbol")) == symbol
            and str(row.get("action")) == action
            and int(row.get("horizon_ms", 0)) == int(horizon_ms)
        ]
        nets = [float(row.get("net_bps", 0.0)) for row in rows]
        n = len(nets)
        if n < self.min_samples:
            return PerformanceGateResult(
                "LEARNING", True, n, 0.0, 0.0, 0.0,
                f"insufficient samples ({n}/{self.min_samples}); paper learning continues",
            )

        mean = sum(nets) / n
        wins = sum(1 for value in nets if value > 0)
        win_rate = wins / n
        if n > 1:
            variance = sum((value - mean) ** 2 for value in nets) / (n - 1)
            std_error = math.sqrt(max(variance, 0.0) / n)
        else:
            std_error = 0.0
        lower_ci = mean - self.confidence_z * std_error

        eligible = (
            mean >= self.min_mean_net_bps
            and win_rate >= self.min_win_rate
            and lower_ci > 0.0
        )
        if eligible:
            return PerformanceGateResult("VALIDATED", True, n, round(mean, 4), round(win_rate, 4), round(lower_ci, 4), "positive expectancy with conservative CI")
        return PerformanceGateResult(
            "REJECTED", False, n, round(mean, 4), round(win_rate, 4), round(lower_ci, 4),
            "failed mean expectancy, win-rate, or lower confidence bound",
        )

    def should_allow(self, symbol: str, action: str, horizon_ms: int) -> PerformanceGateResult:
        result = self.evaluate(symbol, action, horizon_ms)
        if result.status == "LEARNING":
            return result
        if not self.enforce:
            return PerformanceGateResult(
                result.status, True, result.samples, result.mean_net_bps,
                result.win_rate, result.lower_ci_bps, "gate reporting only; enforcement disabled",
            )
        return result
