from PC_ENGINE.core.fast_execution_metrics import FastExecutionMetrics


def test_metrics_track_hot_path_results():
    metrics = FastExecutionMetrics()
    metrics.record(accepted=True, executed=True, reason="executed", latency_ns=10)
    metrics.record(accepted=False, executed=False, reason="stale_event", latency_ns=20)
    metrics.record(accepted=True, executed=False, reason="executor_error:boom", latency_ns=30)

    snapshot = metrics.snapshot()
    assert snapshot.evaluations == 3
    assert snapshot.accepted == 2
    assert snapshot.executed == 1
    assert snapshot.rejected == 1
    assert snapshot.executor_errors == 1
    assert snapshot.max_latency_ns == 30
