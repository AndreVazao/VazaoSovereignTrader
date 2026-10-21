from __future__ import annotations

from scripts.benchmark_runtime_observer_load import percentile, run_scenario, summarize


def test_benchmark_percentile_uses_nearest_rank():
    assert percentile([1_000_000, 2_000_000], 0.50) == 1_000_000
    assert percentile([1_000_000, 2_000_000], 0.99) == 2_000_000
    assert percentile([], 0.99) == 0


def test_benchmark_summary_is_bounded_and_reports_percentiles():
    summary = summarize([10, 20, 30, 40])
    assert summary["count"] == 4
    assert summary["p50_ns"] == 20
    assert summary["p95_ns"] == 40
    assert summary["p99_ns"] == 40
    assert summary["max_ns"] == 40


def test_observer_load_scenario_runs_without_orders_or_reader_leaks():
    result = run_scenario(
        "test_smoke",
        duration_seconds=0.2,
        readers=2,
        token="observer-load-test-token",
    )
    assert result["scenario"] == "test_smoke"
    assert result["runtime_cycle_wrapper_latency"]["count"] > 0
    assert result["http_requests"] > 0
    assert result["http_errors"] == 0
    assert result["reader_threads_still_running"] == 0
    assert "no-op _cycle_once" in result["scope_note"].lower()
