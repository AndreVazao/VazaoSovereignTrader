from __future__ import annotations

from bisect import bisect_left
from dataclasses import dataclass


@dataclass(frozen=True)
class EvidenceObservation:
    evidence_type: str
    evidence_name: str
    symbol: str
    regime: str
    horizon_ms: int
    anchor_timestamp_ms: int
    outcome_timestamp_ms: int
    net_bps: float


@dataclass(frozen=True)
class EvidenceOutcomeStat:
    evidence_type: str
    evidence_name: str
    symbol: str
    regime: str
    horizon_ms: int
    samples: int
    wins: int
    win_rate: float
    mean_net_bps: float
    median_net_bps: float
    lower_ci_bps: float
    eligible: bool


class EvidenceOutcomeEngine:
    """Measure individual PAPER evidence outcomes after costs."""

    def __init__(
        self,
        cost_bps: float = 28.0,
        min_samples: int = 30,
        min_mean_net_bps: float = 0.0,
        min_win_rate: float = 0.50,
    ) -> None:
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

    @staticmethod
    def _index(states: list[dict]) -> dict[str, tuple[list[int], list[float]]]:
        grouped: dict[str, list[tuple[int, float]]] = {}
        for state in states:
            try:
                symbol = str(state.get("symbol", ""))
                ts = int(state.get("timestamp_ms", 0))
                price = float(state.get("price", 0))
            except (TypeError, ValueError):
                continue
            if symbol and ts > 0 and price > 0:
                grouped.setdefault(symbol, []).append((ts, price))
        return {
            symbol: (
                [item[0] for item in ordered],
                [item[1] for item in ordered],
            )
            for symbol, values in grouped.items()
            for ordered in [sorted(values)]
        }

    @staticmethod
    def _extract(state: dict) -> list[tuple[str, str, float]]:
        evidence = state.get("strategy_evidence")
        if not isinstance(evidence, dict):
            return []
        extracted: list[tuple[str, str, float]] = []
        candle = evidence.get("candlestick")
        if isinstance(candle, dict):
            patterns = candle.get("patterns", [])
            if isinstance(patterns, list):
                for pattern in patterns:
                    if not isinstance(pattern, dict):
                        continue
                    name = str(pattern.get("name", ""))
                    direction = str(pattern.get("direction", "")).upper()
                    if name and direction in {"BUY", "SELL"}:
                        extracted.append(("candlestick", name, 1.0 if direction == "BUY" else -1.0))
        amd = evidence.get("amd_phase")
        if isinstance(amd, dict):
            reason = str(amd.get("reason", ""))
            phase = reason.split("phase:", 1)[-1].split(";", 1)[0].strip()
            try:
                score = float(amd.get("score", 0.0))
            except (TypeError, ValueError):
                score = 0.0
            if phase and abs(score) > 0.10:
                extracted.append(("amd_phase", phase, 1.0 if score > 0 else -1.0))
        return extracted

    def observations(
        self,
        states: list[dict],
        horizons_ms: tuple[int, ...] = (1000, 5000, 15000, 60000, 300000),
    ) -> list[EvidenceObservation]:
        index = self._index(states)
        observations: list[EvidenceObservation] = []
        for state in sorted(states, key=lambda row: int(row.get("timestamp_ms", 0))):
            try:
                symbol = str(state.get("symbol", ""))
                regime = str(state.get("regime", "UNKNOWN"))
                ts = int(state.get("timestamp_ms", 0))
                price = float(state.get("price", 0))
            except (TypeError, ValueError):
                continue
            timestamps, prices = index.get(symbol, ([], []))
            if not timestamps or price <= 0:
                continue
            for evidence_type, evidence_name, direction in self._extract(state):
                for horizon in horizons_ms:
                    pos = bisect_left(timestamps, ts + int(horizon))
                    if pos >= len(timestamps):
                        continue
                    future = prices[pos]
                    gross_bps = (future / price - 1.0) * 10000.0
                    net_bps = gross_bps * direction - self.cost_bps
                    observations.append(EvidenceObservation(
                        evidence_type=evidence_type,
                        evidence_name=evidence_name,
                        symbol=symbol,
                        regime=regime,
                        horizon_ms=int(horizon),
                        anchor_timestamp_ms=ts,
                        outcome_timestamp_ms=timestamps[pos],
                        net_bps=net_bps,
                    ))
        return observations

    def evaluate(
        self,
        states: list[dict],
        horizons_ms: tuple[int, ...] = (1000, 5000, 15000, 60000, 300000),
    ) -> list[EvidenceOutcomeStat]:
        observations = self.observations(states, horizons_ms)
        return self.aggregate([
            EvidenceOutcomeStat(
                evidence_type=item.evidence_type,
                evidence_name=item.evidence_name,
                symbol=item.symbol,
                regime=item.regime,
                horizon_ms=item.horizon_ms,
                samples=1,
                wins=int(item.net_bps > 0),
                win_rate=float(item.net_bps > 0),
                mean_net_bps=item.net_bps,
                median_net_bps=item.net_bps,
                lower_ci_bps=item.net_bps,
                eligible=False,
            )
            for item in observations
        ])

    def aggregate(self, observations: list[EvidenceOutcomeStat]) -> list[EvidenceOutcomeStat]:
        groups: dict[tuple[str, str, str, str, int], list[EvidenceOutcomeStat]] = {}
        for row in observations:
            key = (row.evidence_type, row.evidence_name, row.symbol, row.regime, row.horizon_ms)
            groups.setdefault(key, []).append(row)
        result: list[EvidenceOutcomeStat] = []
        for key, rows in sorted(groups.items()):
            values = [float(row.mean_net_bps) for row in rows]
            samples = len(values)
            wins = sum(1 for value in values if value > 0)
            mean = sum(values) / samples if samples else 0.0
            variance = sum((value - mean) ** 2 for value in values) / samples if samples else 0.0
            se = variance ** 0.5 / samples ** 0.5 if samples > 1 else 0.0
            lower = mean - 1.96 * se
            win_rate = wins / samples if samples else 0.0
            eligible = samples >= self.min_samples and mean > self.min_mean_net_bps and win_rate >= self.min_win_rate and lower > 0
            result.append(EvidenceOutcomeStat(
                key[0], key[1], key[2], key[3], key[4],
                samples, wins, round(win_rate, 6), round(mean, 6),
                round(self._median(values), 6), round(lower, 6), eligible,
            ))
        return result
