from __future__ import annotations

from dataclasses import dataclass
from time import monotonic_ns
from typing import Callable, Mapping

from PC_ENGINE.core.fast_path import FastPathDecision, FastPathEngine, FastPathSignal


@dataclass(frozen=True)
class FastExecutionResult:
    accepted: bool
    executed: bool
    reason: str
    decision: FastPathDecision
    latency_ns: int


class FastExecutionRouter:
    """Connects the deterministic fast path to an explicitly supplied executor.

    The router has no exchange access of its own. The caller owns the final
    Risk Engine / mode / guard checks and supplies an executor only when those
    checks have already passed. This keeps the hot path small and prevents an
    accidental bypass of the normal execution controls.
    """

    def __init__(
        self,
        fast_path: FastPathEngine | None = None,
        executor: Callable[[FastPathDecision, Mapping[str, object]], bool] | None = None,
    ) -> None:
        self.fast_path = fast_path or FastPathEngine()
        self.executor = executor

    def handle(
        self,
        event: Mapping[str, object],
        signals: tuple[FastPathSignal, ...],
        *,
        now_ms: int,
        risk_check: Callable[[FastPathSignal, Mapping[str, object]], bool] | None = None,
    ) -> FastExecutionResult:
        started = monotonic_ns()
        decision = self.fast_path.evaluate(
            event,
            signals,
            now_ms=now_ms,
            risk_check=risk_check,
        )
        if not decision.accepted:
            return FastExecutionResult(
                accepted=False,
                executed=False,
                reason=decision.reason,
                decision=decision,
                latency_ns=monotonic_ns() - started,
            )

        if self.executor is None:
            return FastExecutionResult(
                accepted=True,
                executed=False,
                reason="executor_not_configured",
                decision=decision,
                latency_ns=monotonic_ns() - started,
            )

        try:
            executed = bool(self.executor(decision, event))
        except Exception as exc:
            return FastExecutionResult(
                accepted=True,
                executed=False,
                reason=f"executor_error: {exc}",
                decision=decision,
                latency_ns=monotonic_ns() - started,
            )

        return FastExecutionResult(
            accepted=True,
            executed=executed,
            reason="executed" if executed else "executor_rejected",
            decision=decision,
            latency_ns=monotonic_ns() - started,
        )
