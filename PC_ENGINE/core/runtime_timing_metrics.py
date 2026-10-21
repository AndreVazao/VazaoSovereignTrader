from __future__ import annotations

import math
import threading
from collections import deque
from typing import Deque


class RuntimeTimingMetrics:
    """Bounded in-process timing samples; recording never performs I/O.

    Percentiles are calculated only when snapshot() is explicitly requested.
    At most 512 samples per metric are retained, regardless of Runtime uptime.
    """

    _NAMES = ("runtime_cycle", "observer_lock_wait", "observer_lock_hold")
    _CAPACITY = 512

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._samples: dict[str, Deque[int]] = {
            name: deque(maxlen=self._CAPACITY) for name in self._NAMES
        }
        self._counts = {name: 0 for name in self._NAMES}

    def record_ns(self, name: str, duration_ns: int) -> None:
        if name not in self._samples:
            raise ValueError(f"unsupported timing metric: {name}")
        value = max(0, int(duration_ns))
        with self._lock:
            self._samples[name].append(value)
            self._counts[name] += 1

    @staticmethod
    def _percentile(values: list[int], fraction: float) -> int:
        # Nearest-rank percentile: p99 of two samples must include the maximum.
        index = min(len(values) - 1, max(0, math.ceil(len(values) * fraction) - 1))
        return values[index]

    def snapshot(self) -> dict[str, dict[str, int]]:
        """Return detached primitive summaries; sorting happens outside Runtime locks."""
        with self._lock:
            captured = {
                name: (self._counts[name], list(samples))
                for name, samples in self._samples.items()
            }
        result: dict[str, dict[str, int]] = {}
        for name, (count, samples) in captured.items():
            if not samples:
                result[name] = {"count": count, "sample_count": 0, "p50_ns": 0, "p95_ns": 0, "p99_ns": 0, "max_ns": 0}
                continue
            ordered = sorted(samples)
            result[name] = {
                "count": count,
                "sample_count": len(ordered),
                "p50_ns": self._percentile(ordered, 0.50),
                "p95_ns": self._percentile(ordered, 0.95),
                "p99_ns": self._percentile(ordered, 0.99),
                "max_ns": ordered[-1],
            }
        return result
