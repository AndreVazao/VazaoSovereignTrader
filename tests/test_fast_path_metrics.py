from PC_ENGINE.core.fast_path_metrics import FastPathMetrics


def test_metrics_snapshot_reports_latency_and_rejections():
    metrics = FastPathMetrics()
    metrics.record_decision(True, "validated_fast_path", 2_000)
    metrics.record_decision(False, "stale_event", 1_000)
    metrics.record_decision(False, "risk_rejected", 3_000)
    metrics.record_execution(True, 4_000)
    snapshot = metrics.snapshot()
    assert snapshot["evaluated"] == 3
    assert snapshot["accepted"] == 1
    assert snapshot["stale"] == 1
    assert snapshot["risk_rejected"] == 1
    assert snapshot["execution_successes"] == 1
    assert snapshot["avg_evaluation_us"] == 2.0
    assert snapshot["avg_execution_us"] == 4.0
