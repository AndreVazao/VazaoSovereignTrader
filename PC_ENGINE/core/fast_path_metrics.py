from __future__ import annotations

from dataclasses import dataclass, field
from threading import Lock


@dataclass
class FastPathMetrics:
    evaluated: int = 0
    accepted: int = 0
    rejected: int = 0
    stale: int = 0
    risk_rejected: int = 0
    execution_attempts: int = 0
    execution_successes: int = 0
    execution_failures: int = 0
    total_evaluation_ns: int = 0
    total_execution_ns: int = 0
    _lock: Lock = field(default_factory=Lock, init=False, repr=False)

    def record_decision(self, accepted: bool, reason: str, latency_ns: int) -> None:
        with self._lock:
            self.evaluated += 1
            self.accepted += int(accepted)
            self.rejected += int(not accepted)
            self.stale += int(reason == "stale_event")
            self.risk_rejected += int(reason == "risk_rejected")
            self.total_evaluation_ns += max(0, int(latency_ns))

    def record_execution(self, success: bool, latency_ns: int) -> None:
        with self._lock:
            self.execution_attempts += 1
            self.execution_successes += int(success)
            self.execution_failures += int(not success)
            self.total_execution_ns += max(0, int(latency_ns))

    def snapshot(self) -> dict[str, float | int]:
        with self._lock:
            return {
                "evaluated": self.evaluated,
                "accepted": self.accepted,
                "rejected": self.rejected,
                "stale": self.stale,
                "risk_rejected": self.risk_rejected,
                "execution_attempts": self.execution_attempts,
                "execution_successes": self.execution_successes,
                "execution_failures": self.execution_failures,
                "avg_evaluation_us": self.total_evaluation_ns / self.evaluated / 1000 if self.evaluated else 0.0,
                "avg_execution_us": self.total_execution_ns / self.execution_attempts / 1000 if self.execution_attempts else 0.0,
            }
