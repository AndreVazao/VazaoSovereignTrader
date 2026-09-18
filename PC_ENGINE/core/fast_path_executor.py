from __future__ import annotations

from dataclasses import dataclass
from time import monotonic_ns
from typing import Callable, Mapping

from PC_ENGINE.core.fast_path import FastPathDecision


@dataclass(frozen=True)
class FastPathExecutionResult:
    attempted: bool
    accepted: bool
    reason: str
    latency_ns: int
    order_id: str = ""
    qty: float = 0.0
    price: float = 0.0


class FastPathExecutor:
    """Bridges a validated fast-path decision to a caller-owned order function.

    The executor itself has no exchange access and no authority to bypass risk.
    The caller decides whether fast-path execution is enabled and supplies the
    final risk/execution callback. REAL execution is opt-in at the caller.
    """

    def __init__(self, enabled: bool = False, allow_real: bool = False) -> None:
        self.enabled = bool(enabled)
        self.allow_real = bool(allow_real)

    def execute(
        self,
        decision: FastPathDecision,
        event: Mapping[str, object],
        *,
        mode: str,
        authorize: Callable[[FastPathDecision, Mapping[str, object]], tuple[bool, str]] | None,
        order: Callable[[FastPathDecision, Mapping[str, object]], object] | None,
    ) -> FastPathExecutionResult:
        started = monotonic_ns()
        if not self.enabled:
            return self._result(False, False, "fast_path_disabled", started)
        if not decision.accepted:
            return self._result(False, False, "decision_not_accepted", started)
        normalized_mode = str(mode).upper()
        if normalized_mode == "REAL" and not self.allow_real:
            return self._result(False, False, "real_fast_path_disabled", started)
        if normalized_mode not in {"PAPER", "REAL"}:
            return self._result(False, False, "invalid_mode", started)
        if authorize is None or order is None:
            return self._result(False, False, "execution_callbacks_missing", started)
        allowed, reason = authorize(decision, event)
        if not allowed:
            return self._result(False, False, reason or "risk_rejected", started)
        try:
            result = order(decision, event)
        except Exception as exc:
            return self._result(True, False, f"order_error: {exc}", started)
        ok = bool(getattr(result, "ok", False))
        return FastPathExecutionResult(
            attempted=True,
            accepted=ok,
            reason=str(getattr(result, "reason", "order_result")),
            latency_ns=monotonic_ns() - started,
            order_id=str(getattr(result, "order_id", "")),
            qty=float(getattr(result, "qty", 0.0)),
            price=float(getattr(result, "price", 0.0)),
        )

    @staticmethod
    def _result(attempted: bool, accepted: bool, reason: str, started: int) -> FastPathExecutionResult:
        return FastPathExecutionResult(
            attempted=attempted,
            accepted=accepted,
            reason=reason,
            latency_ns=monotonic_ns() - started,
        )
