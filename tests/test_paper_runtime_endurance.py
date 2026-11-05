from __future__ import annotations

from scripts.benchmark_paper_runtime_endurance import run_endurance


def test_paper_runtime_endurance_is_bounded_and_keeps_execution_disabled():
    result = run_endurance(
        duration_seconds=0.2,
        readers=2,
        token="paper-runtime-endurance-test-token",
    )
    assert result["mode"] == "PAPER"
    assert result["engine_cycles"] > 0
    assert result["http_errors"] == 0
    assert result["reader_threads_still_running"] == 0
    assert result["open_positions"] == 0
    assert result["pending_orders"] == 0
    assert result["execution_intents"] == 0
    assert result["python_memory"]["peak_traced_bytes"] > 0
    assert "tracemalloc" in result["python_memory"]["measurement"]
