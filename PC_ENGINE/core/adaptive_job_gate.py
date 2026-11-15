from __future__ import annotations

import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from PC_ENGINE.core.adaptive_resource_manager import AdaptiveResourceManager
from PC_ENGINE.core.process_resource_lease import ProcessResourceLease


class AdaptiveJobDeferred(RuntimeError):
    """Raised when current host capacity does not permit optional heavy work."""


class AdaptiveJobGate:
    """Fail-closed admission gate; policy refresh never interrupts active jobs."""

    _BUDGETS = {
        "backtest": "max_backtest_workers",
        "simulation": "max_simulation_workers",
        "analysis": "max_analysis_workers",
    }

    def __init__(
        self,
        manager: AdaptiveResourceManager,
        *,
        lease_root: str | Path | None = None,
    ):
        self.manager = manager
        configured_root = lease_root if lease_root is not None else getattr(
            manager, "root", None
        )
        if configured_root is None:
            self.lease_root: Path | None = None
        elif lease_root is None:
            self.lease_root = Path(configured_root) / ".runtime" / "resource-leases"
        else:
            self.lease_root = Path(configured_root)
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

        reserved_local = False
        with self._lock:
            if limit > 0 and self._active[kind] < limit:
                self._active[kind] += 1
                reserved_local = True

        lease: ProcessResourceLease | None = None
        admitted = reserved_local
        try:
            if admitted and self.lease_root is not None:
                try:
                    lease = ProcessResourceLease(self.lease_root, kind, limit)
                    admitted = lease.acquire()
                except Exception:
                    admitted = False
            yield admitted
        finally:
            if lease is not None:
                lease.release()
            if reserved_local:
                with self._lock:
                    self._active[kind] = max(0, self._active[kind] - 1)

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "active": dict(self._active),
                "order_authority": False,
                "process_wide_leases": self.lease_root is not None,
            }
