from PC_ENGINE.core.fast_path_metrics import FastPathMetrics


def test_metrics_smoke():
    metrics = FastPathMetrics()
    metrics.record_decision(True, "validated_fast_path", 1000)
    metrics.record_execution(True, 2000)
    snapshot = metrics.snapshot()
    assert snapshot["evaluated"] == 1
    assert snapshot["execution_successes"] == 1
