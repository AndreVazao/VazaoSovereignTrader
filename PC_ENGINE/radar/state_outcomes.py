from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path


@dataclass(frozen=True)
class OutcomeStat:
    symbol: str
    action: str
    regime: str
    horizon_ms: int
    samples: int
    wins: int
    win_rate: float
    mean_net_bps: float
    median_net_bps: float
    lower_ci_bps: float
    eligible: bool


class StateOutcomeEngine:
    """Measure future MarketState returns after round-trip costs.

    PAPER-only descriptive learning. It never creates or authorizes orders.
    """

    def __init__(self, cost_bps: float = 28.0, min_samples: int = 30,
                 min_mean_net_bps: float = 0.0, min_win_rate: float = 0.50) -> None:
        self.cost_bps = max(0.0, float(cost_bps))
        self.min_samples = max(1, int(min_samples))
        self.min_mean_net_bps = float(min_mean_net_bps)
        self.min_win_rate = float(min_win_rate)

    @staticmethod
    def _median(values: list[float]) -> float:
        if not values:
            return 0.0
        ordered = sorted(values)
        mid = len(ordered) // 2
        return ordered[mid] if len(ordered) % 2 else (ordered[mid - 1] + ordered[mid]) / 2.0

    def evaluate(self, states: list[dict], horizons_ms: tuple[int, ...] = (1000, 5000, 15000, 60000, 300000)) -> list[OutcomeStat]:
        by_symbol: dict[str, list[dict]] = {}
        for state in states:
            if state.get("action") not in {"BUY", "SELL"} or float(state.get("price", 0)) <= 0:
                continue
            by_symbol.setdefault(str(state["symbol"]), []).append(state)
        observations: list[OutcomeStat] = []
        for symbol, rows in by_symbol.items():
            rows.sort(key=lambda row: int(row.get("timestamp_ms", 0)))
            for index, state in enumerate(rows):
                t0 = int(state["timestamp_ms"])
                p0 = float(state["price"])
                for horizon in horizons_ms:
                    target = t0 + int(horizon)
                    future = next((row for row in rows[index + 1:] if int(row.get("timestamp_ms", 0)) >= target and float(row.get("price", 0)) > 0), None)
                    if future is None:
                        continue
                    gross_bps = (float(future["price"]) / p0 - 1.0) * 10000.0
                    signed_bps = gross_bps if state["action"] == "BUY" else -gross_bps
                    net_bps = signed_bps - self.cost_bps
                    observations.append(OutcomeStat(symbol, str(state["action"]), str(state.get("regime", "UNKNOWN")), int(horizon), 1, int(net_bps > 0), float(net_bps > 0), net_bps, net_bps, net_bps, False))
        return self.aggregate(observations)

    def aggregate(self, observations: list[OutcomeStat]) -> list[OutcomeStat]:
        groups: dict[tuple[str, str, str, int], list[float]] = {}
        for row in observations:
            groups.setdefault((row.symbol, row.action, row.regime, row.horizon_ms), []).append(row.mean_net_bps)
        output: list[OutcomeStat] = []
        for (symbol, action, regime, horizon), values in sorted(groups.items()):
            samples = len(values)
            wins = sum(value > 0 for value in values)
            win_rate = wins / samples if samples else 0.0
            mean = sum(values) / samples if samples else 0.0
            median = self._median(values)
            variance = sum((value - mean) ** 2 for value in values) / samples if samples else 0.0
            se = (variance ** 0.5) / (samples ** 0.5) if samples > 1 else 0.0
            lower = mean - 1.96 * se
            eligible = samples >= self.min_samples and mean > self.min_mean_net_bps and win_rate >= self.min_win_rate and lower > 0
            output.append(OutcomeStat(symbol, action, regime, horizon, samples, wins, round(win_rate, 6), round(mean, 6), round(median, 6), round(lower, 6), eligible))
        return output

    def save(self, stats: list[OutcomeStat], path: str = "PC_ENGINE/data/radar/state_outcomes.jsonl") -> None:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("w", encoding="utf-8") as handle:
            for stat in stats:
                handle.write(json.dumps(stat.__dict__, separators=(",", ":"), sort_keys=True) + "\n")
