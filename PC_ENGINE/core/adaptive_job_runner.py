from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from PC_ENGINE.core.adaptive_job_gate import AdaptiveJobDeferred, AdaptiveJobGate
from PC_ENGINE.core.adaptive_resource_manager import AdaptiveResourceManager

T = TypeVar("T")


def configured_adaptive_job_gate() -> AdaptiveJobGate | None:
    """Build the configured resource gate; configuration errors fail closed."""
    try:
        from PC_ENGINE.core.config import DATA_DIR, load_config

        config = load_config()
        adaptive = dict(config.get("adaptive_resources", {}))
        if not bool(adaptive.get("enabled", True)):
            return None
        manager = AdaptiveResourceManager(
            root=DATA_DIR,
            reserve_memory_mb=int(adaptive.get("reserve_memory_mb", 512)),
            max_workers_cap=adaptive.get("max_workers_cap"),
        )
        return AdaptiveJobGate(manager)
    except Exception as exc:
        raise AdaptiveJobDeferred(
            f"adaptive resource configuration unavailable: {type(exc).__name__}"
        ) from exc


def _run_with_budget(kind: str, job: Callable[[], T], label: str) -> T:
    gate = configured_adaptive_job_gate()
    if gate is None:
        return job()
    with gate.slot(kind) as admitted:
        if not admitted:
            raise AdaptiveJobDeferred(
                f"{label} deferred by adaptive resource policy ({kind} budget unavailable)"
            )
        return job()


def run_adaptive_simulation(job: Callable[[], T]) -> T:
    """Run optional PAPER simulation only when its current compute budget allows."""
    return _run_with_budget("simulation", job, "PAPER simulation")


def run_adaptive_analysis(job: Callable[[], T]) -> T:
    """Run offline PAPER analysis only when its current compute budget allows."""
    return _run_with_budget("analysis", job, "PAPER analysis")
