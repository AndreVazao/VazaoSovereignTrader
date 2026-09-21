from __future__ import annotations

import json
import statistics
import threading
import time
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class SourceLatencyObservation:
    source_id: str
    symbol: str
    direction: str
    source_ts_ms: int
    market_ts_ms: int
    source_price: float
    market_price: float
    lead_ms: int
    delta_bps: float
    same_direction: bool
    eligible: bool
    observed_ts_ms: int


@dataclass(frozen=True)
class SourceLatencyProfile:
    source_id: str
    symbol: str
    direction: str
    samples: int
    median_lead_ms: float
    p25_lead_ms: float
    p75_lead_ms: float
    mean_delta_bps: float
    median_delta_bps: float
    same_direction_ratio: float
    net_edge_bps: float
    eligible: bool


class ExternalSourceLatencyProfiler:
    """Research-only profiler for timestamped external market information.

    It measures whether an external source consistently moves before a reference
    market feed. It never creates an order, bypasses RiskEngine, or authorizes REAL.
    """

    def __init__(
        self,
        *,
        min_samples: int = 20,
        min_lead_ms: int = 25,
        max_lead_ms: int = 2000,
        min_same_direction_ratio: float = 0.70,
        fee_bps: float = 4.0,
        spread_bps: float = 1.0,
        slippage_bps: float = 1.0,
        execution_buffer_bps: float = 1.0,
        history_limit: int = 5000,
        path: str | Path | None = None,
    ):
        self.min_samples = max(1, int(min_samples))
        self.min_lead_ms = max(0, int(min_lead_ms))
        self.max_lead_ms = max(self.min_lead_ms, int(max_lead_ms))
        self.min_same_direction_ratio = max(0.0, min(1.0, float(min_same_direction_ratio)))
        self.cost_bps = max(0.0, float(fee_bps) + float(spread_bps) + float(slippage_bps) + float(execution_buffer_bps))
        self.history_limit = max(10, int(history_limit))
        self.path = Path(path) if path else None
        if self.path:
            self.path.parent.mkdir(parents=True, exist_ok=True)
        self.profile_path = self.path.with_name("external_source_latency_profiles.jsonl") if self.path else None
        self._history: dict[tuple[str, str, str], list[SourceLatencyObservation]] = {}
        self._lock = threading.RLock()
        self._load_history()

    def _load_history(self) -> None:
        if not self.path or not self.path.exists():
            return
        try:
            with self.path.open("r", encoding="utf-8") as handle:
                for line in handle:
                    try:
                        raw = json.loads(line)
                        observation = SourceLatencyObservation(**raw)
                    except (TypeError, ValueError, json.JSONDecodeError):
                        continue
                    key = (observation.source_id, observation.symbol, observation.direction)
                    rows = self._history.setdefault(key, [])
                    rows.append(observation)
                    if len(rows) > self.history_limit:
                        del rows[:-self.history_limit]
        except OSError:
            return

    @staticmethod
    def _direction(delta_bps: float) -> str:
        if delta_bps > 0:
            return "UP"
        if delta_bps < 0:
            return "DOWN"
        return "FLAT"

    def record(
        self,
        *,
        source_id: str,
        symbol: str,
        source_ts_ms: int,
        source_price: float,
        market_ts_ms: int,
        market_price: float,
        direction: str | None = None,
        observed_ts_ms: int | None = None,
    ) -> SourceLatencyObservation:
        source_id = str(source_id).strip()
        symbol = str(symbol).strip()
        if not source_id or not symbol:
            raise ValueError("source_id_and_symbol_required")
        source_price = float(source_price)
        market_price = float(market_price)
        source_ts_ms = int(source_ts_ms)
        market_ts_ms = int(market_ts_ms)
        if source_price <= 0 or market_price <= 0:
            raise ValueError("prices_must_be_positive")
        if source_ts_ms <= 0 or market_ts_ms <= 0:
            raise ValueError("timestamps_must_be_positive")

        delta_bps = (market_price - source_price) / source_price * 10000.0
        expected = str(direction or self._direction(delta_bps)).upper()
        same_direction = expected in {"UP", "DOWN"} and (
            (expected == "UP" and delta_bps > 0)
            or (expected == "DOWN" and delta_bps < 0)
        )
        lead_ms = market_ts_ms - source_ts_ms
        eligible = self.min_lead_ms <= lead_ms <= self.max_lead_ms and same_direction
        observation = SourceLatencyObservation(
            source_id=source_id,
            symbol=symbol,
            direction=expected,
            source_ts_ms=source_ts_ms,
            market_ts_ms=market_ts_ms,
            source_price=source_price,
            market_price=market_price,
            lead_ms=lead_ms,
            delta_bps=delta_bps,
            same_direction=same_direction,
            eligible=eligible,
            observed_ts_ms=int(observed_ts_ms or time.time() * 1000),
        )
        key = (source_id, symbol, expected)
        with self._lock:
            history = self._history.setdefault(key, [])
            history.append(observation)
            if len(history) > self.history_limit:
                del history[:-self.history_limit]
            if self.path:
                with self.path.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps(asdict(observation), sort_keys=True) + "\n")
            profile = self._profile_locked(key)
            if self.profile_path:
                with self.profile_path.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps(asdict(profile), sort_keys=True) + "\n")
        return observation

    @staticmethod
    def _percentile(values: list[float], percentile: float) -> float:
        if not values:
            return 0.0
        ordered = sorted(values)
        if len(ordered) == 1:
            return ordered[0]
        index = (len(ordered) - 1) * percentile
        lower = int(index)
        upper = min(lower + 1, len(ordered) - 1)
        fraction = index - lower
        return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction

    def _profile_locked(self, key: tuple[str, str, str]) -> SourceLatencyProfile:
        return self._build_profile(key, list(self._history.get(key, [])))

    def _build_profile(self, key: tuple[str, str, str], rows: list[SourceLatencyObservation]) -> SourceLatencyProfile:
        eligible = [row for row in rows if row.eligible]
        leads = [float(row.lead_ms) for row in eligible]
        deltas = [float(row.delta_bps) for row in eligible]
        same_ratio = (
            sum(1 for row in eligible if row.same_direction) / len(eligible)
            if eligible else 0.0
        )
        mean_delta = statistics.fmean(deltas) if deltas else 0.0
        median_delta = statistics.median(deltas) if deltas else 0.0
        median_lead = statistics.median(leads) if leads else 0.0
        net_edge = abs(median_delta) - self.cost_bps
        qualifies = (
            len(eligible) >= self.min_samples
            and median_lead >= self.min_lead_ms
            and median_lead <= self.max_lead_ms
            and same_ratio >= self.min_same_direction_ratio
            and net_edge > 0.0
        )
        return SourceLatencyProfile(
            source_id=key[0],
            symbol=key[1],
            direction=key[2],
            samples=len(eligible),
            median_lead_ms=median_lead,
            p25_lead_ms=self._percentile(leads, 0.25),
            p75_lead_ms=self._percentile(leads, 0.75),
            mean_delta_bps=mean_delta,
            median_delta_bps=median_delta,
            same_direction_ratio=same_ratio,
            net_edge_bps=net_edge,
            eligible=qualifies,
            observed_ts_ms=int(time.time() * 1000),
        )

    def profile(self, source_id: str, symbol: str, direction: str) -> SourceLatencyProfile:
        key = (str(source_id).strip(), str(symbol).strip(), str(direction).upper())
        with self._lock:
            return self._profile_locked(key)
