# Path: PC_ENGINE/radar/hot_path.py
from __future__ import annotations

import json
import threading
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Mapping

from PC_ENGINE.radar.websocket_radar import MarketEvent


@dataclass(frozen=True)
class HotPathOpportunity:
    symbol: str
    leader: str
    follower: str
    direction: str
    leader_move_bps: float
    expected_response_bps: float
    fees_bps: float
    slippage_bps: float
    latency_penalty_bps: float
    expected_net_bps: float
    leader_ts_ms: int
    follower_quote_ts_ms: int
    age_ms: int
    horizon_ms: int
    paper_only: bool = True
    execution_allowed: bool = False
    leader_price: float = 0.0
    follower_entry_price: float = 0.0
    leader_local_ts_ms: int = 0
    follower_entry_local_ts_ms: int = 0


class HotPathLeadLagEngine:
    """In-memory, observation-only lead/lag opportunity detector.

    The hot path never performs disk I/O, research, blocking network calls,
    authentication, or order submission. Learned expectations are supplied
    by the cold path and are treated as advisory evidence only.
    """

    def __init__(
        self,
        *,
        exchanges: list[str],
        lead_window_ms: int = 750,
        stale_after_ms: int = 750,
        min_move_bps: float = 5.0,
        min_expected_net_bps: float = 2.0,
        fee_bps_round_trip: float = 20.0,
        slippage_bps_round_trip: float = 8.0,
        latency_bps_per_100ms: float = 0.5,
        horizon_ms: int = 500,
        data_dir: str | Path = "PC_ENGINE/data/radar",
    ) -> None:
        self.exchanges = tuple(dict.fromkeys(exchanges))
        self.lead_window_ms = max(1, int(lead_window_ms))
        self.stale_after_ms = max(1, int(stale_after_ms))
        self.min_move_bps = max(0.0, float(min_move_bps))
        self.min_expected_net_bps = float(min_expected_net_bps)
        self.fee_bps_round_trip = max(0.0, float(fee_bps_round_trip))
        self.slippage_bps_round_trip = max(0.0, float(slippage_bps_round_trip))
        self.latency_bps_per_100ms = max(0.0, float(latency_bps_per_100ms))
        self.horizon_ms = max(1, int(horizon_ms))
        self.data_dir = Path(data_dir)
        self._latest: dict[tuple[str, str], MarketEvent] = {}
        self._previous: dict[tuple[str, str], float] = {}
        self._expectancy: dict[tuple[str, str, str, str], float] = {}
        self._lock = threading.RLock()
        self._opportunities = 0
        self._last_opportunity: HotPathOpportunity | None = None

    def set_expectancy(
        self,
        *,
        symbol: str,
        leader: str,
        follower: str,
        direction: str,
        expected_response_bps: float,
    ) -> None:
        key = (symbol.upper(), leader.lower(), follower.lower(), direction.upper())
        with self._lock:
            self._expectancy[key] = max(0.0, float(expected_response_bps))

    def set_expectancies(self, rows: Mapping[tuple[str, str, str, str], float]) -> None:
        with self._lock:
            for key, value in rows.items():
                symbol, leader, follower, direction = key
                self._expectancy[(symbol.upper(), leader.lower(), follower.lower(), direction.upper())] = max(0.0, float(value))

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "exchanges": list(self.exchanges),
                "latest_quotes": len(self._latest),
                "expectancy_models": len(self._expectancy),
                "opportunities": self._opportunities,
                "last_opportunity": asdict(self._last_opportunity) if self._last_opportunity else None,
                "paper_only": True,
                "execution_allowed": False,
            }

    def on_market_event(self, event: MarketEvent) -> HotPathOpportunity | None:
        key = (event.exchange, event.symbol)
        with self._lock:
            previous = self._previous.get(key)
            self._previous[key] = event.price
            self._latest[key] = event
            if previous is None or previous <= 0:
                return None

            move_bps = (event.price - previous) / previous * 10000.0
            if abs(move_bps) < self.min_move_bps:
                return None

            direction = "UP" if move_bps > 0 else "DOWN"
            leader = event.exchange.lower()
            best: HotPathOpportunity | None = None

            for follower in self.exchanges:
                follower = follower.lower()
                if follower == leader:
                    continue
                follower_event = self._latest.get((follower, event.symbol))
                if follower_event is None:
                    continue

                age_ms = max(0, event.local_ts_ms - follower_event.local_ts_ms)
                exchange_lag = event.exchange_ts_ms - follower_event.exchange_ts_ms
                if age_ms > self.stale_after_ms:
                    continue
                if exchange_lag < 0 or exchange_lag > self.lead_window_ms:
                    continue

                expected = self._expectancy.get(
                    (event.symbol.upper(), leader, follower, direction), 0.0
                )
                if expected <= 0:
                    continue

                latency_penalty = max(0.0, event.local_receive_latency_ms / 100.0) * self.latency_bps_per_100ms
                net = expected - self.fee_bps_round_trip - self.slippage_bps_round_trip - latency_penalty
                if net < self.min_expected_net_bps:
                    continue

                candidate = HotPathOpportunity(
                    symbol=event.symbol,
                    leader=leader,
                    follower=follower,
                    direction=direction,
                    leader_move_bps=round(move_bps, 4),
                    expected_response_bps=round(expected, 4),
                    fees_bps=round(self.fee_bps_round_trip, 4),
                    slippage_bps=round(self.slippage_bps_round_trip, 4),
                    latency_penalty_bps=round(latency_penalty, 4),
                    expected_net_bps=round(net, 4),
                    leader_ts_ms=event.exchange_ts_ms,
                    follower_quote_ts_ms=follower_event.exchange_ts_ms,
                    age_ms=age_ms,
                    horizon_ms=self.horizon_ms,
                    leader_price=float(event.price),
                    follower_entry_price=float(follower_event.price),
                    leader_local_ts_ms=int(event.local_ts_ms),
                    follower_entry_local_ts_ms=int(follower_event.local_ts_ms),
                )
                if best is None or candidate.expected_net_bps > best.expected_net_bps:
                    best = candidate

            if best is not None:
                self._opportunities += 1
                self._last_opportunity = best
            return best

    def persist(self, opportunity: HotPathOpportunity) -> None:
        """Cold-path persistence; intentionally never called by on_market_event."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        path = self.data_dir / "hot_path_opportunities.jsonl"
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(opportunity), ensure_ascii=False, sort_keys=True) + "\n")
