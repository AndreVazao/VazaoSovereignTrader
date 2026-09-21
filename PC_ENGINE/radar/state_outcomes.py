from __future__ import annotations

from bisect import bisect_left
from dataclasses import dataclass
import json
from pathlib import Path
import time


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
    observed_at_ms: int = 0


class StateOutcomeEngine:
    """Evaluate historical MarketState observations without creating orders.

    Outcomes are measured from the first future observation for the same symbol
    at or after each target horizon. Results are net of a configurable
    round-trip cost and are descriptive PAPER-learning evidence only.
    """

    def __init__(self, cost_bps: float = 28.0, min_samples: int = 30,
                 min_mean_net_bps: float = 0.0, min_win_rate: float = 0.50) -> None:
        self.cost_bps = max(0.0, float(cost_bps))
        self.min_samples = max(1, int(min_samples))
        self.min_mean_net_bps = float(min_mean_net_bps)
        self.min_win_rate = float(min_win_rate)

    @staticmethod
    def _percentile(values: list[float], p: float) -> float:
        if not values:
            return 0.0
        values = sorted(values)
        index = (len(values) - 1) * p
        lo, hi = int(index), min(int(index) + 1, len(values) - 1)
        frac = index - lo
        return values[lo] + (values[hi] - values[lo]) * frac

    @staticmethod
    def _mean(values: list[float]) -> float:
        return sum(values) / len(values) if values else 0.0

    @staticmethod
    def _index_by_symbol(states: list[dict]) -> dict[str, tuple[list[int], list[float]]]:
        grouped: dict[str, list[tuple[int, float]]] = {}
        for state in states:
            symbol = str(state.get("symbol", ""))
            timestamp = int(state.get("timestamp_ms", 0))
            price = float(state.get("price", 0))
            if symbol and timestamp > 0 and price > 0:
                grouped.setdefault(symbol, []).append((timestamp, price))
        return {
            symbol: (
                [item[0] for item in ordered],
                [item[1] for item in ordered],
            )
            for symbol, values in grouped.items()
            for ordered in [sorted(values)]
        }

    def evaluate(self, states: list[dict], horizons_ms: tuple[int, ...] = (1000, 5000, 15000, 60000, 300000)) -> list[OutcomeStat]:
        ordered = sorted(
            (s for s in states if float(s.get("price", 0)) > 0 and s.get("action") in {"BUY", "SELL"}),
            key=lambda s: int(s.get("timestamp_ms", 0)),
        )
        index = self._index_by_symbol(states)
        observations: list[OutcomeStat] = []
        for state in ordered:
            action = str(state["action"])
            symbol = str(state["symbol"])
            regime = str(state.get("regime", "UNKNOWN"))
            t0 = int(state["timestamp_ms"])
            p0 = float(state["price"])
            timestamps, prices = index.get(symbol, ([], []))
            if not timestamps:
                continue
            for horizon in horizons_ms:
                pos = bisect_left(timestamps, t0 + int(horizon))
                if pos >= len(timestamps):
                    continue
                p1 = prices[pos]
                gross_bps = ((p1 / p0) - 1.0) * 10000.0
                signed_bps = gross_bps if action == "BUY" else -gross_bps
                net_bps = signed_bps - self.cost_bps
                observations.append(OutcomeStat(
                    symbol, action, regime, int(horizon), 1,
                    int(net_bps > 0), float(net_bps > 0),
                    net_bps, net_bps, net_bps, False,
                ))
        return self.aggregate(observations)

    def aggregate(self, observations: list[OutcomeStat]) -> list[OutcomeStat]:
        groups: dict[tuple[str, str, str, int], list[OutcomeStat]] = {}
        for row in observations:
            groups.setdefault((row.symbol, row.action, row.regime, row.horizon_ms), []).append(row)
        output: list[OutcomeStat] = []
        for (symbol, action, regime, horizon), rows in sorted(groups.items()):
            values = [r.mean_net_bps for r in rows]
            samples = len(values)
            wins = sum(1 for v in values if v > 0)
            win_rate = wins / samples if samples else 0.0
            mean = self._mean(values)
            median = self._percentile(values, 0.50)
            variance = self._mean([(v - mean) ** 2 for v in values]) if samples else 0.0
            se = (variance ** 0.5) / (samples ** 0.5) if samples > 1 else 0.0
            lower = mean - 1.96 * se
            eligible = samples >= self.min_samples and mean > self.min_mean_net_bps and win_rate >= self.min_win_rate and lower > 0
            output.append(OutcomeStat(symbol, action, regime, horizon, samples, wins, round(win_rate, 6), round(mean, 6), round(median, 6), round(lower, 6), eligible, int(time.time() * 1000)))
        return output

    def save(self, stats: list[OutcomeStat], path: str = "PC_ENGINE/data/radar/state_outcomes.jsonl") -> None:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("w", encoding="utf-8") as handle:
            for stat in stats:
                handle.write(json.dumps(stat.__dict__, separators=(",", ":"), sort_keys=True) + "\n")
