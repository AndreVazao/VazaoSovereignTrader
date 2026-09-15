from PC_ENGINE.core.fast_execution_metrics import FastExecutionMetrics


def test_metrics_snapshot_is_stable():
    metrics = FastExecutionMetrics()
    metrics.record(accepted=False, executed=False, reason="stale_event", latency_ns=7)
    snapshot = metrics.snapshot()
    assert snapshot.evaluations == 1
    assert snapshot.rejected == 1
    assert snapshot.max_latency_ns == 7
