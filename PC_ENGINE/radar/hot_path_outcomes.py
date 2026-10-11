# Path: PC_ENGINE/radar/hot_path_outcomes.py
from __future__ import annotations

import math
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
        """Accept only internally consistent, finite PAPER opportunities."""
        try:
            symbol = str(opportunity.symbol).strip().upper()
            leader = str(opportunity.leader).strip().lower()
            follower = str(opportunity.follower).strip().lower()
            direction = str(opportunity.direction).strip().upper()
            horizon_ms = int(opportunity.horizon_ms)
            leader_local_ts_ms = int(opportunity.leader_local_ts_ms)
            follower_entry_local_ts_ms = int(opportunity.follower_entry_local_ts_ms)
            age_ms = int(opportunity.age_ms)
            leader_price = float(opportunity.leader_price)
            entry_price = float(opportunity.follower_entry_price)
            expected_response_bps = float(opportunity.expected_response_bps)
            expected_net_bps = float(opportunity.expected_net_bps)
            fee_bps = float(opportunity.fees_bps)
            slippage_bps = float(opportunity.slippage_bps)
            latency_penalty_bps = float(opportunity.latency_penalty_bps)
            leader_move_bps = float(opportunity.leader_move_bps)
        except (AttributeError, TypeError, ValueError, OverflowError):
            return False

        numeric_values = (
            leader_price, entry_price, expected_response_bps, expected_net_bps,
            fee_bps, slippage_bps, latency_penalty_bps, leader_move_bps,
        )
        expected_net_from_costs = expected_response_bps - fee_bps - slippage_bps - latency_penalty_bps
        if (
            not opportunity.paper_only
            or opportunity.execution_allowed
            or not symbol
            or not leader
            or not follower
            or leader == follower
            or direction not in {"UP", "DOWN"}
            or horizon_ms <= 0
            or leader_local_ts_ms <= 0
            or follower_entry_local_ts_ms <= 0
            or follower_entry_local_ts_ms > leader_local_ts_ms
            or age_ms < 0
            or age_ms != leader_local_ts_ms - follower_entry_local_ts_ms
            or leader_price <= 0.0
            or entry_price <= 0.0
            or not all(math.isfinite(value) for value in numeric_values)
            or min(fee_bps, slippage_bps, latency_penalty_bps) < 0.0
            or not math.isclose(expected_net_bps, expected_net_from_costs, rel_tol=1e-4, abs_tol=0.02)
        ):
            return False

        row = asdict(opportunity)
        row["symbol"] = symbol
        row["leader"] = leader
        row["follower"] = follower
        row["direction"] = direction
        row["horizon_ms"] = horizon_ms
        row["leader_local_ts_ms"] = leader_local_ts_ms
        row["follower_entry_local_ts_ms"] = follower_entry_local_ts_ms
        row["age_ms"] = age_ms
        row["target_local_ts_ms"] = leader_local_ts_ms + horizon_ms
        row["registered_local_ts_ms"] = leader_local_ts_ms
        with self._lock:
            if len(self._pending) >= self.max_pending:
                self._pending.pop(0)
                self._dropped += 1
            self._pending.append(row)
            self._registered += 1
        return True

    def on_market_event(self, event: MarketEvent) -> None:
        """Resolve outcomes only when a valid later follower quote crosses the horizon."""
        exchange = str(event.exchange).strip().lower()
        symbol = str(event.symbol).strip().upper()
        try:
            local_ts_ms = int(event.local_ts_ms)
            price = float(event.price)
        except (TypeError, ValueError, OverflowError):
            return
        if (
            not exchange
            or not symbol
            or local_ts_ms <= 0
            or not math.isfinite(price)
            or price <= 0.0
        ):
            return

        with self._lock:
            remaining: list[dict[str, Any]] = []
            for pending in self._pending:
                if symbol != str(pending["symbol"]).strip().upper():
                    remaining.append(pending)
                    continue
                if exchange != str(pending["follower"]).strip().lower():
                    remaining.append(pending)
                    continue
                target = int(pending["target_local_ts_ms"])
                if local_ts_ms < target:
                    remaining.append(pending)
                    continue
                entry = float(pending["follower_entry_price"])
                if not math.isfinite(entry) or entry <= 0:
                    remaining.append(pending)
                    continue
                direction_sign = 1.0 if str(pending["direction"]).upper() == "UP" else -1.0
                response_bps = direction_sign * (price - entry) / entry * 10000.0
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

    def peek_completed(self, limit: int = 2048) -> list[dict[str, Any]]:
        """Return a stable prefix without removing it, so failed disk writes can retry."""
        with self._lock:
            count = max(1, int(limit))
            return [dict(row) for row in self._completed[:count]]

    def acknowledge_completed(self, count: int) -> int:
        """Remove only records confirmed persisted by the cold-path writer."""
        with self._lock:
            amount = min(len(self._completed), max(0, int(count)))
            del self._completed[:amount]
            return amount

    def drain_completed(self, limit: int = 2048) -> list[dict[str, Any]]:
        # Compatibility helper for callers that intentionally consume in memory.
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
