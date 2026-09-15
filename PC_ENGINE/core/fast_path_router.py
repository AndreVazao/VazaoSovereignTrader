from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Mapping, Sequence

from PC_ENGINE.core.fast_path import FastPathEngine, FastPathSignal
from PC_ENGINE.core.fast_path_executor import FastPathExecutionResult, FastPathExecutor
from PC_ENGINE.core.fast_path_metrics import FastPathMetrics


@dataclass(frozen=True)
class FastPathRouteResult:
    decision_reason: str
    execution: FastPathExecutionResult


class FastPathRouter:
    """Synchronous, bounded router for already validated lead/lag signals."""

    def __init__(self, settings: Mapping[str, object]) -> None:
        self.engine = FastPathEngine(
            min_confidence=float(settings.get("min_confidence", 0.75)),
            min_expectancy_bps=float(settings.get("min_expectancy_bps", 2.0)),
            max_signal_age_ms=int(settings.get("max_signal_age_ms", 1000)),
        )
        self.executor = FastPathExecutor(
            enabled=bool(settings.get("enabled", False)),
            allow_real=bool(settings.get("allow_real", False)),
        )
        self.metrics = FastPathMetrics()

    def route(
        self,
        event: Mapping[str, object],
        signals: Sequence[FastPathSignal],
        *,
        now_ms: int,
        mode: str,
        risk_check: Callable[[FastPathSignal, Mapping[str, object]], bool] | None = None,
        authorize: Callable[[object, Mapping[str, object]], tuple[bool, str]] | None = None,
        order: Callable[[object, Mapping[str, object]], object] | None = None,
    ) -> FastPathRouteResult:
        decision = self.engine.evaluate(event, signals, now_ms=now_ms, risk_check=risk_check)
        self.metrics.record_decision(decision.accepted, decision.reason, decision.evaluation_ns)
        execution = self.executor.execute(
            decision,
            event,
            mode=mode,
            authorize=authorize,
            order=order,
        )
        if execution.attempted:
            self.metrics.record_execution(execution.accepted, execution.latency_ns)
        return FastPathRouteResult(decision.reason, execution)
