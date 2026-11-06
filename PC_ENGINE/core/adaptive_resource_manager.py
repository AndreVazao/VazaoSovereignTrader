from __future__ import annotations

import os
import platform
import shutil
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable


@dataclass(frozen=True)
class ResourceSnapshot:
    cpu_count: int
    memory_total_mb: int
    memory_available_mb: int
    disk_free_mb: int
    cpu_load_pct: float | None
    os_name: str
    sampled_at: float


@dataclass(frozen=True)
class ResourcePolicy:
    profile: str
    max_workers: int
    max_backtest_workers: int
    max_simulation_workers: int
    max_analysis_workers: int
    memory_budget_mb: int
    defer_heavy_jobs: bool
    reasons: tuple[str, ...]

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["reasons"] = list(self.reasons)
        payload["allow_real"] = False
        payload["auto_promote_real"] = False
        return payload


def _memory_mb() -> tuple[int, int]:
    try:
        import psutil  # type: ignore
        memory = psutil.virtual_memory()
        return int(memory.total / 1048576), int(memory.available / 1048576)
    except Exception:
        if hasattr(os, "sysconf"):
            try:
                page = int(os.sysconf("SC_PAGE_SIZE"))
                total = int(os.sysconf("SC_PHYS_PAGES")) * page
                available = int(os.sysconf("SC_AVPHYS_PAGES")) * page
                return total // 1048576, available // 1048576
            except (ValueError, OSError, AttributeError):
                pass
        return 0, 0


def _cpu_load_pct() -> float | None:
    try:
        import psutil  # type: ignore
        return float(psutil.cpu_percent(interval=None))
    except Exception:
        try:
            if hasattr(os, "getloadavg"):
                load = os.getloadavg()[0]
                return max(0.0, min(100.0, load / max(1, os.cpu_count() or 1) * 100.0))
        except (OSError, AttributeError):
            pass
        return None


def detect_system_resources(
    *, root: str | Path = ".", cpu_load_reader: Callable[[], float | None] = _cpu_load_pct
) -> ResourceSnapshot:
    total_mb, available_mb = _memory_mb()
    try:
        disk_free_mb = int(shutil.disk_usage(Path(root)).free / 1048576)
    except OSError:
        disk_free_mb = 0
    return ResourceSnapshot(
        cpu_count=max(1, os.cpu_count() or 1),
        memory_total_mb=max(0, total_mb),
        memory_available_mb=max(0, available_mb),
        disk_free_mb=max(0, disk_free_mb),
        cpu_load_pct=cpu_load_reader(),
        os_name=platform.system() or "unknown",
        sampled_at=time.time(),
    )


def derive_resource_policy(
    snapshot: ResourceSnapshot,
    *,
    reserve_memory_mb: int = 512,
    max_workers_cap: int | None = None,
) -> ResourcePolicy:
    """Derive compute budgets only; never changes trading/risk permissions."""
    cpu = max(1, int(snapshot.cpu_count))
    total = max(0, int(snapshot.memory_total_mb))
    available = max(0, int(snapshot.memory_available_mb))
    free_disk = max(0, int(snapshot.disk_free_mb))
    load = snapshot.cpu_load_pct
    reasons: list[str] = []

    # Unknown memory measurements are treated as constrained, never as spare capacity.
    constrained_memory = total <= 0 or total < 6144
    low_headroom = available <= 0 or available < max(1024, reserve_memory_mb * 2)
    constrained_cpu = cpu <= 2
    overloaded = load is not None and load >= 85.0
    disk_constrained = free_disk > 0 and free_disk < 2048

    if total <= 0:
        reasons.append("memory_total_unavailable")
    elif constrained_memory:
        reasons.append("limited_total_memory")
    if available <= 0:
        reasons.append("memory_available_unavailable")
    elif low_headroom:
        reasons.append("limited_available_memory")
    if constrained_cpu:
        reasons.append("limited_cpu")
    if overloaded:
        reasons.append("high_cpu_load")
    if disk_constrained:
        reasons.append("limited_disk_space")

    if constrained_memory or low_headroom or constrained_cpu or overloaded or disk_constrained:
        profile = "COMPACT"
        workers = 1 if constrained_memory or constrained_cpu else 2
        backtests = simulations = 0
        analysis = 1 if not overloaded else 0
        defer_heavy = True
    elif total >= 16384 and available >= 8192 and cpu >= 8 and not overloaded:
        profile = "PERFORMANCE"
        workers = min(cpu, 12)
        backtests = min(max(1, cpu // 4), 4)
        simulations = min(max(1, cpu // 4), 4)
        analysis = min(max(1, cpu // 2), 6)
        defer_heavy = False
        reasons.append("sufficient_compute_headroom")
    else:
        profile = "BALANCED"
        workers = min(cpu, 4)
        backtests = 1
        simulations = 1
        analysis = min(2, workers)
        defer_heavy = False
        reasons.append("moderate_compute_headroom")

    if max_workers_cap is not None:
        cap = max(1, int(max_workers_cap))
        workers = min(workers, cap)
        backtests = min(backtests, cap)
        simulations = min(simulations, cap)
        analysis = min(analysis, cap)

    memory_budget = max(0, available - max(0, reserve_memory_mb))
    if memory_budget == 0:
        backtests = simulations = analysis = 0
        defer_heavy = True
        if "insufficient_memory_after_reserve" not in reasons:
            reasons.append("insufficient_memory_after_reserve")

    return ResourcePolicy(
        profile=profile,
        max_workers=max(1, workers),
        max_backtest_workers=max(0, backtests),
        max_simulation_workers=max(0, simulations),
        max_analysis_workers=max(0, analysis),
        memory_budget_mb=memory_budget,
        defer_heavy_jobs=defer_heavy,
        reasons=tuple(reasons),
    )


class AdaptiveResourceManager:
    """Refreshable resource policy provider with injectable probes for tests."""

    def __init__(
        self,
        *,
        root: str | Path = ".",
        reserve_memory_mb: int = 512,
        max_workers_cap: int | None = None,
        sampler: Callable[..., ResourceSnapshot] = detect_system_resources,
    ) -> None:
        self.root = Path(root)
        self.reserve_memory_mb = max(0, int(reserve_memory_mb))
        self.max_workers_cap = max_workers_cap
        self._sampler = sampler
        self.snapshot: ResourceSnapshot | None = None
        self.policy: ResourcePolicy | None = None

    def refresh(self) -> ResourcePolicy:
        snapshot = self._sampler(root=self.root)
        policy = derive_resource_policy(
            snapshot,
            reserve_memory_mb=self.reserve_memory_mb,
            max_workers_cap=self.max_workers_cap,
        )
        self.snapshot = snapshot
        self.policy = policy
        return policy

    def status(self) -> dict:
        if self.snapshot is None or self.policy is None:
            self.refresh()
        assert self.snapshot is not None and self.policy is not None
        return {
            "snapshot": asdict(self.snapshot),
            "policy": self.policy.to_dict(),
            "permissions_changed": False,
            "trading_mode_changed": False,
        }
