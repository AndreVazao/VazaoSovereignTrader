from __future__ import annotations

import threading
from contextlib import contextmanager
from typing import Iterator

from PC_ENGINE.core.adaptive_resource_manager import AdaptiveResourceManager


class AdaptiveJobDeferred(RuntimeError):
    """Raised when current host capacity does not permit optional heavy work."""


class AdaptiveJobGate:
    """Fail-closed admission gate; policy refresh never interrupts active jobs."""

    _BUDGETS = {
        "backtest": "max_backtest_workers",
        "simulation": "max_simulation_workers",
        "analysis": "max_analysis_workers",
    }

    def __init__(self, manager: AdaptiveResourceManager):
        self.manager = manager
        self._lock = threading.Lock()
        self._active = {"backtest": 0, "simulation": 0, "analysis": 0}

    @contextmanager
    def slot(self, kind: str) -> Iterator[bool]:
        if kind not in self._BUDGETS:
            raise ValueError(f"unsupported adaptive job kind: {kind}")
        try:
            policy = self.manager.refresh()
            limit = max(0, int(getattr(policy, self._BUDGETS[kind])))
        except Exception:
            yield False
            return

        admitted = False
        with self._lock:
            if limit > 0 and self._active[kind] < limit:
                self._active[kind] += 1
                admitted = True
        try:
            yield admitted
        finally:
            if admitted:
                with self._lock:
                    self._active[kind] = max(0, self._active[kind] - 1)

    def snapshot(self) -> dict:
        with self._lock:
            return {"active": dict(self._active), "order_authority": False}
