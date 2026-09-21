from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from statistics import mean
from typing import Iterable


@dataclass(frozen=True)
class LatencyObservation:
    symbol: str
    leader: str
    follower: str
    direction: str
    lead_ms: int
    receive_lead_ms: int
    lead_bps: float
    follower_bps: float
    net_expected_edge_bps: float
    sample_count: int
    same_direction_ratio: float
    persistence_ratio: float
    eligible: bool


class LatencyEdgeDetector:
    """Measure temporal lead candidates; never authorizes orders.

    The detector deliberately uses only observed public-feed timing and
    configurable execution-cost assumptions. It is a research/PAPER component.
    """

    def __init__(
        self,
        *,
        min_lead_bps: float = 1.0,
        max_lead_ms: int = 750,
        min_samples: int = 20,
        min_same_direction_ratio: float = 0.70,
        min_persistence_ratio: float = 0.60,
        fee_bps: float = 4.0,
        spread_bps: float = 1.0,
        slippage_bps: float = 1.0,
        execution_latency_ms: int = 100,
        latency_decay_bps_per_100ms: float = 0.25,
        history_size: int = 5000,
    ) -> None:
        self.min_lead_bps = float(min_lead_bps)
        self.max_lead_ms = int(max_lead_ms)
        self.min_samples = int(min_samples)
        self.min_same_direction_ratio = float(min_same_direction_ratio)
        self.min_persistence_ratio = float(min_persistence_ratio)
        self.fee_bps = float(fee_bps)
        self.spread_bps = float(spread_bps)
        self.slippage_bps = float(slippage_bps)
        self.execution_latency_ms = int(execution_latency_ms)
        self.latency_decay_bps_per_100ms = float(latency_decay_bps_per_100ms)
        self._history: dict[tuple[str, str, str, str], deque[tuple[int, float, float]]] = defaultdict(
            lambda: deque(maxlen=history_size)
        )

    def observe(
        self,
        *,
        symbol: str,
        leader: str,
        follower: str,
        direction: str,
        lead_ms: int,
        leader_move_bps: float,
        follower_move_bps: float,
        receive_lead_ms: int | None = None,
    ) -> LatencyObservation:
        lead_ms = int(lead_ms)
        receive_lead_ms = lead_ms if receive_lead_ms is None else int(receive_lead_ms)
        leader_move_bps = float(leader_move_bps)
        follower_move_bps = float(follower_move_bps)
        key = (symbol.upper(), leader.lower(), follower.lower(), direction.upper())
        history = self._history[key]

        same_direction = (
            leader_move_bps != 0
            and follower_move_bps != 0
            and leader_move_bps * follower_move_bps > 0
        )
        persistence = (
            abs(follower_move_bps) >= abs(leader_move_bps) * 0.25
            and same_direction
        )
        history.append((lead_ms, leader_move_bps, follower_move_bps))

        relevant = list(history)
        same_ratio = (
            sum(1 for _, leader_bps, follower_bps in relevant
                if leader_bps != 0 and follower_bps != 0 and leader_bps * follower_bps > 0)
            / len(relevant)
            if relevant else 0.0
        )
        persistence_ratio = (
            sum(
                1
                for _, leader_bps, follower_bps in relevant
                if leader_bps != 0
                and follower_bps != 0
                and leader_bps * follower_bps > 0
                and abs(follower_bps) >= abs(leader_bps) * 0.25
            )
            / len(relevant)
            if relevant else 0.0
        )

        gross_edge_bps = min(abs(leader_move_bps), abs(follower_move_bps))
        latency_decay = (
            self.execution_latency_ms / 100.0
        ) * self.latency_decay_bps_per_100ms
        net_edge = gross_edge_bps - (
            self.fee_bps + self.spread_bps + self.slippage_bps + latency_decay
        )

        eligible = (
            lead_ms <= self.max_lead_ms
            and receive_lead_ms >= 0
            and receive_lead_ms <= self.max_lead_ms
            and receive_lead_ms >= 0
            and receive_lead_ms <= self.max_lead_ms
            and gross_edge_bps >= self.min_lead_bps
            and len(relevant) >= self.min_samples
            and same_ratio >= self.min_same_direction_ratio
            and persistence_ratio >= self.min_persistence_ratio
            and net_edge > 0
        )
        return LatencyObservation(
            symbol=symbol.upper(),
            leader=leader.lower(),
            follower=follower.lower(),
            direction=direction.upper(),
            lead_ms=lead_ms,
            receive_lead_ms=receive_lead_ms,
            lead_bps=round(gross_edge_bps, 4),
            follower_bps=round(follower_move_bps, 4),
            net_expected_edge_bps=round(net_edge, 4),
            sample_count=len(relevant),
            same_direction_ratio=round(same_ratio, 4),
            persistence_ratio=round(persistence_ratio, 4),
            eligible=eligible,
        )

    def observe_event(self, event: object) -> LatencyObservation:
        return self.observe(
            symbol=event.symbol,
            leader=event.leader,
            follower=event.follower,
            direction=event.direction,
            lead_ms=event.exchange_lag_ms,
            receive_lead_ms=event.receive_lag_ms,
            leader_move_bps=event.leader_move_bps,
            follower_move_bps=event.follower_move_bps,
        )

    def history(self, symbol: str, leader: str, follower: str, direction: str = "UP") -> Iterable[tuple[int, float, float]]:
        return tuple(self._history[(symbol.upper(), leader.lower(), follower.lower(), direction.upper())])
