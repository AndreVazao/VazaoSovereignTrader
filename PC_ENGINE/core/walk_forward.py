from __future__ import annotations

import json
import math
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class WalkForwardWindow:
    train_start_ms: int
    train_end_ms: int
    validation_start_ms: int
    validation_end_ms: int


@dataclass(frozen=True)
class WalkForwardResult:
    symbol: str
    action: str
    horizon_ms: int
    train_samples: int
    validation_samples: int
    train_mean_net_bps: float
    validation_mean_net_bps: float
    validation_win_rate: float
    validation_lower_ci_bps: float
    passed: bool
    reason: str


class WalkForwardEvaluator:
    """Out-of-sample evaluator for PAPER confluence outcomes.

    Outcomes are split chronologically. No validation row can influence the
    training statistics used to decide whether a setup is robust.
    This module is descriptive only and never authorizes an order.
    """

    def __init__(
        self,
        data_dir: str | Path = "PC_ENGINE/data/radar",
        train_fraction: float = 0.70,
        min_train_samples: int = 50,
        min_validation_samples: int = 30,
        min_validation_mean_bps: float = 0.0,
        min_validation_win_rate: float = 0.50,
        require_positive_lower_ci: bool = True,
    ) -> None:
        self.data_dir = Path(data_dir)
        self.path = self.data_dir / "confluence_outcomes.jsonl"
        self.train_fraction = min(0.90, max(0.50, float(train_fraction)))
        self.min_train_samples = max(1, int(min_train_samples))
        self.min_validation_samples = max(1, int(min_validation_samples))
        self.min_validation_mean_bps = float(min_validation_mean_bps)
        self.min_validation_win_rate = float(min_validation_win_rate)
        self.require_positive_lower_ci = bool(require_positive_lower_ci)

    def _read(self) -> list[dict[str, Any]]:
        path = self.path
        if not path.exists():
            return []
        rows: list[dict[str, Any]] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                row = json.loads(line)
                if isinstance(row, dict) and float(row.get("net_bps", 0.0)) == float(row.get("net_bps", 0.0)):
                    rows.append(row)
            except (ValueError, TypeError, json.JSONDecodeError):
                continue
        rows.sort(key=lambda x: int(x.get("evaluated_ts_ms", x.get("ts_ms", 0))))
        return rows

    @staticmethod
    def _lower_ci(values: list[float]) -> float:
        if not values:
            return 0.0
        mean = sum(values) / len(values)
        if len(values) < 2:
            return mean
        variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
        se = math.sqrt(variance / len(values))
        return mean - 1.96 * se

    def evaluate(self) -> dict[str, Any]:
        rows = self._read()
        grouped: dict[tuple[str, str, int], list[dict[str, Any]]] = {}
        for row in rows:
            key = (str(row.get("symbol", "")), str(row.get("action", "HOLD")), int(row.get("horizon_ms", 0)))
            grouped.setdefault(key, []).append(row)

        results: list[WalkForwardResult] = []
        for (symbol, action, horizon), values in grouped.items():
            if action not in {"BUY", "SELL"}:
                continue
            split = max(1, int(len(values) * self.train_fraction))
            train = values[:split]
            validation = values[split:]
            train_nets = [float(x.get("net_bps", 0.0)) for x in train]
            val_nets = [float(x.get("net_bps", 0.0)) for x in validation]
            val_wins = sum(1 for x in validation if float(x.get("net_bps", 0.0)) > 0)
            train_mean = sum(train_nets) / len(train_nets) if train_nets else 0.0
            val_mean = sum(val_nets) / len(val_nets) if val_nets else 0.0
            win_rate = val_wins / len(validation) if validation else 0.0
            lower = self._lower_ci(val_nets)

            reasons: list[str] = []
            if len(train) < self.min_train_samples:
                reasons.append("insufficient_train_samples")
            if len(validation) < self.min_validation_samples:
                reasons.append("insufficient_validation_samples")
            if val_mean <= self.min_validation_mean_bps:
                reasons.append("validation_expectancy_not_positive")
            if win_rate < self.min_validation_win_rate:
                reasons.append("validation_win_rate_below_threshold")
            if self.require_positive_lower_ci and lower <= 0:
                reasons.append("validation_ci_not_positive")

            results.append(WalkForwardResult(
                symbol=symbol,
                action=action,
                horizon_ms=horizon,
                train_samples=len(train),
                validation_samples=len(validation),
                train_mean_net_bps=round(train_mean, 4),
                validation_mean_net_bps=round(val_mean, 4),
                validation_win_rate=round(win_rate, 4),
                validation_lower_ci_bps=round(lower, 4),
                passed=not reasons,
                reason=";".join(reasons) if reasons else "passed",
            ))

        payload = {
            "generated_ts_ms": int(time.time() * 1000),
            "train_fraction": self.train_fraction,
            "results": [r.__dict__ for r in results],
        }
        self.data_dir.mkdir(parents=True, exist_ok=True)
        (self.data_dir / "walk_forward_results.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return payload

    def eligible(self, symbol: str, action: str, horizon_ms: int) -> bool:
        payload = self.evaluate()
        return any(
            row["symbol"] == symbol
            and row["action"] == action
            and int(row["horizon_ms"]) == int(horizon_ms)
            and bool(row["passed"])
            for row in payload["results"]
        )
