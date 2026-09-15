from __future__ import annotations

import json
import math
import time
from pathlib import Path
from typing import Any

from PC_ENGINE.radar.regime_engine import MarketRegimeEngine


class RegimeAwareValidator:
    """Evaluates PAPER outcomes separately by market regime.

    If historical rows already contain a `regime` field it is used. Otherwise
    the validator can infer a regime from a JSON `returns` array stored in the
    row. It never creates or authorizes orders.
    """

    def __init__(
        self,
        data_dir: str | Path = "PC_ENGINE/data/radar",
        min_samples: int = 30,
        min_mean_net_bps: float = 0.0,
        min_win_rate: float = 0.50,
        require_positive_lower_ci: bool = True,
    ) -> None:
        self.data_dir = Path(data_dir)
        self.path = self.data_dir / "confluence_outcomes.jsonl"
        self.min_samples = max(1, int(min_samples))
        self.min_mean_net_bps = float(min_mean_net_bps)
        self.min_win_rate = float(min_win_rate)
        self.require_positive_lower_ci = bool(require_positive_lower_ci)
        self.regime_engine = MarketRegimeEngine()

    def _read(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        rows: list[dict[str, Any]] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            try:
                row = json.loads(line)
                if isinstance(row, dict):
                    rows.append(row)
            except json.JSONDecodeError:
                continue
        return rows

    def _regime(self, row: dict[str, Any]) -> str:
        explicit = str(row.get("regime", "")).strip()
        if explicit:
            return explicit
        raw = row.get("returns")
        if isinstance(raw, list):
            try:
                return self.regime_engine.classify([float(x) for x in raw]).name
            except (TypeError, ValueError):
                pass
        return "UNKNOWN"

    @staticmethod
    def _lower_ci(values: list[float]) -> float:
        if not values:
            return 0.0
        mean = sum(values) / len(values)
        if len(values) < 2:
            return mean
        variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
        return mean - 1.96 * math.sqrt(variance / len(values))

    def evaluate(self) -> dict[str, Any]:
        groups: dict[tuple[str, str, int, str], list[dict[str, Any]]] = {}
        for row in self._read():
            action = str(row.get("action", "HOLD"))
            if action not in {"BUY", "SELL"}:
                continue
            key = (
                str(row.get("symbol", "")),
                action,
                int(row.get("horizon_ms", 0)),
                self._regime(row),
            )
            groups.setdefault(key, []).append(row)

        results: list[dict[str, Any]] = []
        for (symbol, action, horizon, regime), rows in groups.items():
            nets = [float(row.get("net_bps", 0.0)) for row in rows]
            mean_net = sum(nets) / len(nets) if nets else 0.0
            wins = sum(1 for value in nets if value > 0)
            win_rate = wins / len(nets) if nets else 0.0
            lower = self._lower_ci(nets)
            reasons: list[str] = []
            if len(nets) < self.min_samples:
                reasons.append("insufficient_samples")
            if mean_net <= self.min_mean_net_bps:
                reasons.append("expectancy_not_positive")
            if win_rate < self.min_win_rate:
                reasons.append("win_rate_below_threshold")
            if self.require_positive_lower_ci and lower <= 0:
                reasons.append("ci_not_positive")
            results.append({
                "symbol": symbol,
                "action": action,
                "horizon_ms": horizon,
                "regime": regime,
                "samples": len(nets),
                "wins": wins,
                "win_rate": round(win_rate, 4),
                "mean_net_bps": round(mean_net, 4),
                "lower_ci_bps": round(lower, 4),
                "passed": not reasons,
                "reason": ";".join(reasons) if reasons else "passed",
            })

        results.sort(key=lambda x: (x["passed"], x["mean_net_bps"], x["samples"]), reverse=True)
        payload = {"generated_ts_ms": int(time.time() * 1000), "results": results}
        self.data_dir.mkdir(parents=True, exist_ok=True)
        (self.data_dir / "regime_validation_results.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return payload
