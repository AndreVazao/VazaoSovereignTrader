from __future__ import annotations

import threading

from PC_ENGINE.core.runtime_timing_metrics import RuntimeTimingMetrics


def test_runtime_timing_metrics_are_bounded_and_report_percentiles():
    metrics = RuntimeTimingMetrics()

    for value in range(1000):
        metrics.record_ns("runtime_cycle", value)

    summary = metrics.snapshot()["runtime_cycle"]
    assert summary["count"] == 1000
    assert summary["sample_count"] == 512
    assert summary["p50_ns"] >= 488
    assert summary["p95_ns"] >= 970
    assert summary["p99_ns"] >= 990
    assert summary["max_ns"] == 999


def test_runtime_timing_metrics_snapshots_are_detached_and_thread_safe():
    metrics = RuntimeTimingMetrics()
    workers = [
        threading.Thread(
            target=lambda: [metrics.record_ns("observer_lock_wait", 7) for _ in range(500)]
        )
        for _ in range(4)
    ]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join(timeout=2)
    assert all(not worker.is_alive() for worker in workers)

    first = metrics.snapshot()
    first["observer_lock_wait"]["count"] = -1
    second = metrics.snapshot()["observer_lock_wait"]
    assert second["count"] == 2000
    assert second["sample_count"] == 512
    assert second["max_ns"] == 7


def test_runtime_timing_metrics_reject_unknown_names():
    metrics = RuntimeTimingMetrics()
    try:
        metrics.record_ns("unbounded-user-input", 1)
    except ValueError:
        pass
    else:
        raise AssertionError("unknown metric names must be rejected")
