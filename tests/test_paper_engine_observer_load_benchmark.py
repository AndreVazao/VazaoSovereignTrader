from __future__ import annotations

from scripts.benchmark_paper_engine_observer_load import percentile, run_scenario, summarize


def test_percentile_and_summary_use_nearest_rank():
    assert percentile([1_000_000, 2_000_000], 0.50) == 1_000_000
    assert percentile([1_000_000, 2_000_000], 0.99) == 2_000_000
    assert summarize([10, 20, 30, 40])["p95_ns"] == 40
    assert summarize([])["count"] == 0


def test_full_paper_engine_cycle_survives_observer_polling_without_orders():
    result = run_scenario(
        "test_smoke",
        duration_seconds=0.2,
        readers=2,
        token="paper-observer-load-test-token",
    )
    assert result["mode"] == "PAPER"
    assert result["engine_cycles"] > 0
    assert result["runtime_cycle_latency"]["count"] == result["engine_cycles"]
    assert result["synthetic_market_data_calls"]["ohlcv"] > 0
    assert result["strategy_symbols_evaluated_last_cycle"] > 0
    assert result["http_requests"] > 0
    assert result["http_errors"] == 0
    assert result["reader_threads_still_running"] == 0
    assert result["open_positions"] == 0
    assert result["pending_orders"] == 0
    assert result["execution_intents"] == 0
    assert "full sovereignengine paper cycle" in result["scope_note"].lower()
