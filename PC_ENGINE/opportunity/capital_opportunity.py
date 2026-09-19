from __future__ import annotations

import json
import math
import statistics
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class OpportunityCandidate:
    symbol: str
    leader: str
    follower: str
    direction: str
    samples: int
    median_lag_ms: float
    consistency: float
    median_gross_move_bps: float
    estimated_cost_bps: float
    estimated_net_edge_bps: float
    required_capital: float
    capital_efficiency_bps_per_1000: float
    status: str
    reason: str


class CapitalOpportunityEngine:
    """Find evidence-backed, capital-efficient candidate opportunities.

    Advisory only. Never places orders.
    """

    def __init__(
        self,
        observations_path: str | Path = "PC_ENGINE/data/radar/observations.jsonl",
        output_path: str | Path = "PC_ENGINE/data/radar/capital_opportunities.jsonl",
        min_samples: int = 30,
        max_lag_ms: int = 2000,
        min_net_edge_bps: float = 2.0,
        fee_bps: float = 10.0,
        spread_bps: float = 4.0,
        slippage_bps: float = 5.0,
        latency_buffer_bps: float = 3.0,
        default_required_capital: float = 100.0,
        required_capital_by_venue: dict[str, float] | None = None,
    ) -> None:
        self.observations_path = Path(observations_path)
        self.output_path = Path(output_path)
        self.min_samples = max(1, int(min_samples))
        self.max_lag_ms = max(1, int(max_lag_ms))
        self.min_net_edge_bps = float(min_net_edge_bps)
        self.estimated_cost_bps = sum(
            float(value)
            for value in (fee_bps, spread_bps, slippage_bps, latency_buffer_bps)
        )
        self.default_required_capital = max(0.0, float(default_required_capital))
        self.required_capital_by_venue = {
            str(key): max(0.0, float(value))
            for key, value in (required_capital_by_venue or {}).items()
        }

    @staticmethod
    def _finite(value: Any, default: float = 0.0) -> float:
        try:
            result = float(value)
            return result if math.isfinite(result) else default
        except (TypeError, ValueError):
            return default

    def _required_capital(self, follower: str) -> float:
        return self.required_capital_by_venue.get(
            follower, self.default_required_capital
        )

    def load(self) -> list[dict[str, Any]]:
        if not self.observations_path.exists():
            return []
        rows: list[dict[str, Any]] = []
        with self.observations_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(row, dict):
                    rows.append(row)
        return rows

    def analyze(self) -> list[OpportunityCandidate]:
        groups: dict[tuple[str, str, str, str], list[dict[str, float]]] = {}
        for row in self.load():
            for event in row.get("lead_lag", []):
                if not isinstance(event, dict):
                    continue
                lag = self._finite(event.get("lag_ms"), -1)
                gross = abs(self._finite(event.get("follower_return_pct"), 0.0)) * 100.0
                leader = str(event.get("leader", ""))
                follower = str(event.get("follower", ""))
                symbol = str(event.get("symbol", ""))
                direction = str(event.get("direction", ""))
                if not leader or not follower or not symbol or lag < 0:
                    continue
                if lag > self.max_lag_ms:
                    continue
                key = (symbol, leader, follower, direction)
                groups.setdefault(key, []).append({"lag": lag, "gross": gross})

        candidates: list[OpportunityCandidate] = []
        for (symbol, leader, follower, direction), events in groups.items():
            samples = len(events)
            if samples < self.min_samples:
                continue
            lags = [item["lag"] for item in events]
            gross_values = [item["gross"] for item in events]
            median_lag = statistics.median(lags)
            median_gross = statistics.median(gross_values)
            consistency = sum(value > 0 for value in gross_values) / samples
            net_edge = median_gross - self.estimated_cost_bps
            required_capital = self._required_capital(follower)
            efficiency = (
                net_edge / required_capital * 1000.0
                if required_capital > 0
                else 0.0
            )
            if net_edge >= self.min_net_edge_bps and consistency >= 0.6:
                status = "CANDIDATE"
                reason = "historical evidence survives the configured cost model"
            else:
                status = "WATCH"
                reason = "insufficient net edge or consistency after costs"
            candidates.append(
                OpportunityCandidate(
                    symbol=symbol,
                    leader=leader,
                    follower=follower,
                    direction=direction,
                    samples=samples,
                    median_lag_ms=round(median_lag, 3),
                    consistency=round(consistency, 4),
                    median_gross_move_bps=round(median_gross, 4),
                    estimated_cost_bps=round(self.estimated_cost_bps, 4),
                    estimated_net_edge_bps=round(net_edge, 4),
                    required_capital=round(required_capital, 2),
                    capital_efficiency_bps_per_1000=round(efficiency, 4),
                    status=status,
                    reason=reason,
                )
            )

        candidates.sort(
            key=lambda item: (
                item.status != "CANDIDATE",
                -item.capital_efficiency_bps_per_1000,
                -item.samples,
            )
        )
        self._persist(candidates)
        return candidates

    def _persist(self, candidates: list[OpportunityCandidate]) -> None:
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        row = {
            "generated_at_ms": time.time_ns() // 1_000_000,
            "estimated_cost_bps": self.estimated_cost_bps,
            "candidates": [asdict(candidate) for candidate in candidates],
        }
        with self.output_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
