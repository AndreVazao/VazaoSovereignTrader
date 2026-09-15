from __future__ import annotations

from dataclasses import dataclass
from threading import Lock


@dataclass(frozen=True)
class FastExecutionMetricsSnapshot:
    evaluations: int
    accepted: int
    executed: int
    rejected: int
    executor_errors: int
    max_latency_ns: int


class FastExecutionMetrics:
    """Tiny lock-protected counters for hot-path observability."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._evaluations = 0
        self._accepted = 0
        self._executed = 0
        self._rejected = 0
        self._executor_errors = 0
        self._max_latency_ns = 0

    def record(self, *, accepted: bool, executed: bool, reason: str, latency_ns: int) -> None:
        with self._lock:
            self._evaluations += 1
            self._accepted += int(accepted)
            self._executed += int(executed)
            self._rejected += int(not accepted)
            self._executor_errors += int(reason.startswith("executor_error:"))
            self._max_latency_ns = max(self._max_latency_ns, int(latency_ns))

    def snapshot(self) -> FastExecutionMetricsSnapshot:
        with self._lock:
            return FastExecutionMetricsSnapshot(
                evaluations=self._evaluations,
                accepted=self._accepted,
                executed=self._executed,
                rejected=self._rejected,
                executor_errors=self._executor_errors,
                max_latency_ns=self._max_latency_ns,
            )
