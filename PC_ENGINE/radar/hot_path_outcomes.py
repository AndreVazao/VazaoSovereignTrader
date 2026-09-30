# Path: PC_ENGINE/radar/hot_path_outcomes.py
from __future__ import annotations

import threading
from dataclasses import asdict
from typing import Any

from PC_ENGINE.radar.hot_path import HotPathOpportunity
from PC_ENGINE.radar.websocket_radar import MarketEvent


class HotPathOutcomeTracker:
    """Bounded, in-memory PAPER outcome tracker; never submits orders or performs I/O."""

    def __init__(self, *, max_pending: int = 4096, max_completed: int = 8192) -> None:
        self.max_pending = max(1, int(max_pending))
        self.max_completed = max(1, int(max_completed))
        self._pending: list[dict[str, Any]] = []
        self._completed: list[dict[str, Any]] = []
        self._lock = threading.RLock()
        self._registered = 0
        self._timed_out = 0
        self._dropped = 0

    def register(self, opportunity: HotPathOpportunity) -> bool:
        if (
            not opportunity.paper_only
            or opportunity.execution_allowed
            or opportunity.follower_entry_price <= 0
            or opportunity.leader_local_ts_ms <= 0
        ):
            return False
        row = asdict(opportunity)
        row["target_local_ts_ms"] = int(opportunity.leader_local_ts_ms + opportunity.horizon_ms)
        row["registered_local_ts_ms"] = int(opportunity.leader_local_ts_ms)
        with self._lock:
            if len(self._pending) >= self.max_pending:
                self._pending.pop(0)
                self._dropped += 1
            self._pending.append(row)
            self._registered += 1
        return True

    def on_market_event(self, event: MarketEvent) -> None:
        """Resolve outcomes only when a later follower quote crosses the horizon."""
        with self._lock:
            remaining: list[dict[str, Any]] = []
            for pending in self._pending:
                if event.symbol.upper() != str(pending["symbol"]).upper():
                    remaining.append(pending)
                    continue
                if event.exchange.lower() != str(pending["follower"]).lower():
                    remaining.append(pending)
                    continue
                target = int(pending["target_local_ts_ms"])
                if int(event.local_ts_ms) < target:
                    remaining.append(pending)
                    continue
                entry = float(pending["follower_entry_price"])
                if entry <= 0 or float(event.price) <= 0:
                    remaining.append(pending)
                    continue
                direction_sign = 1.0 if str(pending["direction"]).upper() == "UP" else -1.0
                response_bps = direction_sign * (float(event.price) - entry) / entry * 10000.0
                cost_bps = (
                    float(pending["fees_bps"])
                    + float(pending["slippage_bps"])
                    + float(pending["latency_penalty_bps"])
                )
                realized_net_bps = response_bps - cost_bps
                expected_net_bps = float(pending["expected_net_bps"])
                self._completed.append({
                    "schema_version": 1,
                    "status": "COMPLETED",
                    "paper_only": True,
                    "orders_submitted": False,
                    "symbol": pending["symbol"],
                    "leader": pending["leader"],
                    "follower": pending["follower"],
                    "direction": pending["direction"],
                    "leader_move_bps": float(pending["leader_move_bps"]),
                    "expected_response_bps": float(pending["expected_response_bps"]),
                    "expected_net_bps": expected_net_bps,
                    "realized_response_bps": round(response_bps, 6),
                    "realized_net_bps": round(realized_net_bps, 6),
                    "edge_error_bps": round(realized_net_bps - expected_net_bps, 6),
                    "fees_bps": float(pending["fees_bps"]),
                    "slippage_bps": float(pending["slippage_bps"]),
                    "latency_penalty_bps": float(pending["latency_penalty_bps"]),
                    "entry_price": entry,
                    "outcome_price": float(event.price),
                    "entry_local_ts_ms": int(pending["follower_entry_local_ts_ms"]),
                    "leader_local_ts_ms": int(pending["leader_local_ts_ms"]),
                    "outcome_local_ts_ms": int(event.local_ts_ms),
                    "horizon_ms": int(pending["horizon_ms"]),
                    "observed_horizon_ms": int(event.local_ts_ms) - int(pending["leader_local_ts_ms"]),
                    "profitable_after_costs": realized_net_bps > 0.0,
                    "expected_edge_met": realized_net_bps >= expected_net_bps,
                })
                if len(self._completed) > self.max_completed:
                    del self._completed[: len(self._completed) - self.max_completed]
                    self._dropped += 1
            self._pending = remaining

    def drain_completed(self, limit: int = 2048) -> list[dict[str, Any]]:
        with self._lock:
            count = max(1, int(limit))
            rows = self._completed[:count]
            del self._completed[:count]
            return rows

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "pending": len(self._pending),
                "completed_buffered": len(self._completed),
                "max_pending": self.max_pending,
                "max_completed": self.max_completed,
                "registered": self._registered,
                "timed_out": self._timed_out,
                "dropped_overflow": self._dropped,
                "paper_only": True,
                "orders_submitted": False,
            }
