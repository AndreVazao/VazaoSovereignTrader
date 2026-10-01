from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from .surface_adapter_registry import get_adapter_registration, instantiate_adapter
from .surface_adapters import ExecutionSurfaceAdapter, Surface, SurfaceFeedback

@dataclass
class AdapterRuntimeRecord:
    runtime_id: str
    surface: Surface
    venue_id: str
    state: str = "REGISTERED"
    instance_created_at_ms: int | None = None
    last_feedback_at_ms: int | None = None
    last_feedback_state: str | None = None
    last_feedback_acknowledged: bool | None = None
    error: str | None = None

class ExecutionSurfaceRuntime:
    """Explicit PAPER adapter lifecycle; never an execution-authorization path.

    Registration is inert. Instantiation is explicit and does not call probe(),
    observe(), execute(), launch a process, open a browser, or invoke ADB.
    Transport probing is a separate explicit operation.
    """

    def __init__(self) -> None:
        self._adapters: dict[str, ExecutionSurfaceAdapter] = {}
        self._records: dict[str, AdapterRuntimeRecord] = {}

    @staticmethod
    def _now_ms() -> int:
        return int(time.time() * 1000)

    def instantiate(self, *, runtime_id: str, surface: Surface, config: Any) -> AdapterRuntimeRecord:
        runtime_id = str(runtime_id or "").strip()
        if not runtime_id:
            raise ValueError("runtime_id is required")
        if runtime_id in self._records:
            raise ValueError(f"runtime_id already used: {runtime_id}")
        registration = get_adapter_registration(surface)
        if registration is None:
            raise ValueError(f"no adapter registered for surface={surface.value}")
        if not registration.paper_only:
            raise RuntimeError("runtime lifecycle only accepts PAPER adapters")
        adapter = instantiate_adapter(surface, config)
        adapter_surface = getattr(adapter, "surface", None)
        if adapter_surface is not surface:
            raise RuntimeError(f"adapter surface mismatch: expected={surface.value}")
        venue_id = str(getattr(config, "venue_id", "") or "").strip()
        if not venue_id:
            raise ValueError("adapter config venue_id is required")
        record = AdapterRuntimeRecord(runtime_id=runtime_id, surface=surface, venue_id=venue_id, state="INSTANTIATED", instance_created_at_ms=self._now_ms())
        self._adapters[runtime_id] = adapter
        self._records[runtime_id] = record
        return record

    def probe(self, runtime_id: str) -> SurfaceFeedback:
        runtime_id = str(runtime_id or "").strip()
        adapter = self._adapters.get(runtime_id)
        if adapter is None:
            raise KeyError(f"runtime adapter not instantiated: {runtime_id}")
        try:
            feedback = adapter.probe()
        except Exception as exc:
            record = self._records[runtime_id]
            record.state = "PROBE_FAILED"
            record.error = f"{type(exc).__name__}: {exc}"
            raise
        record = self._records[runtime_id]
        record.state = "PROBED"
        record.last_feedback_at_ms = feedback.observed_at_ms
        record.last_feedback_state = feedback.state
        record.last_feedback_acknowledged = feedback.acknowledged
        record.error = None
        return feedback

    def close(self, runtime_id: str) -> None:
        runtime_id = str(runtime_id or "").strip()
        adapter = self._adapters.pop(runtime_id, None)
        record = self._records.get(runtime_id)
        if adapter is None:
            raise KeyError(f"runtime adapter not instantiated: {runtime_id}")
        close = getattr(adapter, "close", None)
        if callable(close):
            close()
        if record is not None:
            record.state = "CLOSED"

    def snapshot(self) -> dict[str, Any]:
        return {
            "observational_only": True, "paper_only": True, "orders_submitted": False,
            "execution_authorized": False,
            "adapters": [
                {"runtime_id": r.runtime_id, "surface": r.surface.value, "venue_id": r.venue_id,
                 "state": r.state, "instance_created_at_ms": r.instance_created_at_ms,
                 "last_feedback_at_ms": r.last_feedback_at_ms, "last_feedback_state": r.last_feedback_state,
                 "last_feedback_acknowledged": r.last_feedback_acknowledged, "error": r.error}
                for r in self._records.values()
            ],
        }

    def get(self, runtime_id: str) -> ExecutionSurfaceAdapter | None:
        return self._adapters.get(str(runtime_id or "").strip())