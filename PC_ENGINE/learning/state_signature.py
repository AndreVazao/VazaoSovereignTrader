from __future__ import annotations

from bisect import bisect_left
from dataclasses import dataclass
from math import sqrt
from statistics import median
from typing import Iterable

@dataclass(frozen=True)
class SignatureStat:
    signature: str
    horizon_ms: int
    samples: int
    wins: int
    win_rate: float
    mean_net_bps: float
    median_net_bps: float
    lower_ci_bps: float
    eligible: bool

class StateSignature:
    """Stable, low-cardinality representation of a MarketState."""
    SCORE_FIELDS = (
        "technical_score", "candlestick_bias", "radar_pressure",
        "lead_lag_score", "momentum_score", "mean_reversion_score",
        "order_flow_score", "breakout_score", "derivatives_score",
    )

    @staticmethod
    def _bucket(value: float) -> str:
        value = float(value)
        if value <= -0.60: return "N"
        if value <= -0.20: return "n"
        if value < 0.20: return "0"
        if value < 0.60: return "p"
        return "P"

    @classmethod
    def build(cls, state: dict) -> str:
        parts = [
            str(state.get("regime", "UNKNOWN")),
            str(state.get("trend", "UNKNOWN")),
            str(state.get("volatility", "UNKNOWN")),
            str(state.get("action", "HOLD")),
            f"c{cls._bucket(state.get('confluence_score', 0.0))}",
            f"q{cls._bucket(float(state.get('confluence_confidence', 0.0)) * 2.0 - 1.0)}",
        ]
        parts.extend(f"{name}={cls._bucket(state.get(name, 0.0))}" for name in cls.SCORE_FIELDS)
        return "|".join(parts)

    @classmethod
    def hierarchy(cls, state: dict) -> tuple[str, ...]:
        full = cls.build(state)
        base = "|".join(full.split("|")[:4])
        action = str(state.get("action", "HOLD"))
        regime = str(state.get("regime", "UNKNOWN"))
        return (full, base + "|action=" + action, regime + "|action=" + action, regime)

class StateSignatureLearningEngine:
    """Descriptive PAPER learning; never places orders or changes risk."""
    def __init__(self, *, cost_bps: float = 28.0, min_samples: int = 30, min_mean_net_bps: float = 0.0, min_win_rate: float = 0.50) -> None:
        self.cost_bps = max(0.0, float(cost_bps))
        self.min_samples = max(1, int(min_samples))
        self.min_mean_net_bps = float(min_mean_net_bps)
        self.min_win_rate = float(min_win_rate)

    @staticmethod
    def _ci_lower(values: list[float]) -> float:
        if len(values) < 2: return values[0] if values else 0.0
        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        return mean - 1.96 * sqrt(variance / len(values))

    @staticmethod
    def _index(states: Iterable[dict]) -> dict[str, tuple[list[int], list[float]]]:
        grouped: dict[str, list[tuple[int, float]]] = {}
        for row in states:
            symbol = str(row.get("symbol", "")); ts = int(row.get("timestamp_ms", 0)); price = float(row.get("price", 0.0))
            if symbol and ts > 0 and price > 0: grouped.setdefault(symbol, []).append((ts, price))
        return {symbol: ([x[0] for x in ordered], [x[1] for x in ordered]) for symbol, values in grouped.items() for ordered in [sorted(values)]}

    def evaluate(self, states: list[dict], horizons_ms: tuple[int, ...] = (5000, 15000, 60000)) -> list[SignatureStat]:
        ordered = sorted((row for row in states if str(row.get("action", "HOLD")) in {"BUY", "SELL"} and float(row.get("price", 0.0)) > 0), key=lambda row: int(row.get("timestamp_ms", 0)))
        index = self._index(states); grouped: dict[tuple[str, int], list[float]] = {}
        for state in ordered:
            symbol = str(state["symbol"]); timestamps, prices = index.get(symbol, ([], []))
            if not timestamps: continue
            t0 = int(state["timestamp_ms"]); p0 = float(state["price"]); direction = 1.0 if state["action"] == "BUY" else -1.0
            for horizon in horizons_ms:
                pos = bisect_left(timestamps, t0 + int(horizon))
                if pos >= len(timestamps): continue
                gross = ((prices[pos] / p0) - 1.0) * 10000.0; net = direction * gross - self.cost_bps
                for signature in StateSignature.hierarchy(state): grouped.setdefault((signature, int(horizon)), []).append(net)
        output: list[SignatureStat] = []
        for (signature, horizon), values in sorted(grouped.items()):
            samples = len(values); wins = sum(v > 0 for v in values); mean = sum(values) / samples; win_rate = wins / samples; lower = self._ci_lower(values)
            output.append(SignatureStat(signature, horizon, samples, wins, round(win_rate, 6), round(mean, 6), round(median(values), 6), round(lower, 6), samples >= self.min_samples and mean > self.min_mean_net_bps and win_rate >= self.min_win_rate and lower > 0))
        return output

    def rank(self, state: dict, stats: list[SignatureStat], *, horizon_ms: int = 5000) -> SignatureStat | None:
        for signature in StateSignature.hierarchy(state):
            matches = [row for row in stats if row.signature == signature and row.horizon_ms == int(horizon_ms) and row.eligible]
            if matches: return max(matches, key=lambda row: (row.samples, row.lower_ci_bps))
        return None
