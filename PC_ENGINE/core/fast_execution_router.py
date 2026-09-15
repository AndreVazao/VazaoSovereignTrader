from __future__ import annotations

from dataclasses import dataclass
from time import monotonic_ns
from typing import Callable, Mapping

from PC_ENGINE.core.fast_execution_metrics import FastExecutionMetrics
from PC_ENGINE.core.fast_path import FastPathDecision, FastPathEngine, FastPathSignal


@dataclass(frozen=True)
class FastExecutionResult:
    accepted: bool
    executed: bool
    reason: str
    decision: FastPathDecision
    latency_ns: int


class FastExecutionRouter:
    """Connect the deterministic fast path to an explicitly supplied executor.

    The router has no exchange access of its own. The caller owns the final
    Risk Engine / mode / guard checks and supplies an executor only when those
    checks have already passed. This prevents accidental bypass of controls.
    """

    def __init__(
        self,
        fast_path: FastPathEngine | None = None,
        executor: Callable[[FastPathDecision, Mapping[str, object]], bool] | None = None,
        metrics: FastExecutionMetrics | None = None,
    ) -> None:
        self.fast_path = fast_path or FastPathEngine()
        self.executor = executor
        self.metrics = metrics

    def handle(
        self,
        event: Mapping[str, object],
        signals: tuple[FastPathSignal, ...],
        *,
        now_ms: int,
        risk_check: Callable[[FastPathSignal, Mapping[str, object]], bool] | None = None,
    ) -> FastExecutionResult:
        started = monotonic_ns()
        decision = self.fast_path.evaluate(event, signals, now_ms=now_ms, risk_check=risk_check)
        if not decision.accepted:
            result = FastExecutionResult(False, False, decision.reason, decision, monotonic_ns() - started)
            self._record(result)
            return result

        if self.executor is None:
            result = FastExecutionResult(True, False, "executor_not_configured", decision, monotonic_ns() - started)
            self._record(result)
            return result

        try:
            executed = bool(self.executor(decision, event))
        except Exception as exc:
            result = FastExecutionResult(True, False, f"executor_error: {exc}", decision, monotonic_ns() - started)
            self._record(result)
            return result

        result = FastExecutionResult(True, executed, "executed" if executed else "executor_rejected", decision, monotonic_ns() - started)
        self._record(result)
        return result

    def _record(self, result: FastExecutionResult) -> None:
        if self.metrics is not None:
            self.metrics.record(
                accepted=result.accepted,
                executed=result.executed,
                reason=result.reason,
                latency_ns=result.latency_ns,
            )
