from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Tuple

from PC_ENGINE.market_events.normalized import MarketEvent


@dataclass(frozen=True)
class LeadLagSignal:
    symbol: str
    leader: str
    follower: str
    direction: str
    leader_event_id: str
    follower_event_id: str
    lag_ms: float
    leader_return_bps: float
    confidence: float


class RealtimeLeadLagEngine:
    """Detect short-lived cross-venue directional propagation."""

    def __init__(self, *, max_lag_ms: float = 750.0, min_move_bps: float = 5.0,
                 min_confidence: float = 0.60) -> None:
        self.max_lag_ms = max_lag_ms
        self.min_move_bps = min_move_bps
        self.min_confidence = min_confidence
        self._last_price: Dict[Tuple[str, str], float] = {}
        self._last_move: Dict[Tuple[str, str], Tuple[MarketEvent, float, str]] = {}

    @staticmethod
    def _direction(previous: float, current: float) -> Optional[str]:
        if current > previous:
            return "UP"
        if current < previous:
            return "DOWN"
        return None

    @staticmethod
    def _event_time_ms(event: MarketEvent) -> float:
        if event.exchange_ts_ms is not None:
            return float(event.exchange_ts_ms)
        if event.provider_ts_ms is not None:
            return float(event.provider_ts_ms)
        return event.local_receive_wall_ns / 1_000_000.0

    @staticmethod
    def _price(event: MarketEvent) -> Optional[float]:
        if event.price is not None:
            return event.price
        if event.bid is not None and event.ask is not None:
            return (event.bid + event.ask) / 2.0
        return None

    def observe(self, event: MarketEvent) -> Optional[LeadLagSignal]:
        price = self._price(event)
        if price is None or price <= 0:
            return None

        key = (event.venue, event.symbol)
        previous = self._last_price.get(key)
        self._last_price[key] = price
        if previous is None:
            return None

        move_bps = (price - previous) / previous * 10_000
        direction = self._direction(previous, price)
        if direction is None:
            return None

        signal = None
        current_ts = self._event_time_ms(event)

        for (venue, symbol), (leader_event, leader_move_bps, leader_direction) in list(self._last_move.items()):
            if symbol != event.symbol or venue == event.venue:
                continue
            lag_ms = current_ts - self._event_time_ms(leader_event)
            if (leader_direction == direction and 0 < lag_ms <= self.max_lag_ms
                    and abs(leader_move_bps) >= self.min_move_bps
                    and abs(move_bps) >= self.min_move_bps):
                confidence = min(1.0, abs(leader_move_bps) / max(self.min_move_bps, 1.0))
                if confidence >= self.min_confidence:
                    signal = LeadLagSignal(
                        symbol=event.symbol, leader=venue, follower=event.venue,
                        direction=direction, leader_event_id=leader_event.event_id,
                        follower_event_id=event.event_id, lag_ms=lag_ms,
                        leader_return_bps=leader_move_bps, confidence=confidence,
                    )

        if abs(move_bps) >= self.min_move_bps:
            self._last_move[key] = (event, move_bps, direction)
        return signal
