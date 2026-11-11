from __future__ import annotations

from PC_ENGINE.research.strategy_discovery import discover_strategy


def _states(count: int = 180):
    rows = []
    price = 100.0
    for index in range(count):
        price *= 1.001 if index % 5 else 0.999
        rows.append({
            "symbol": "BTC/USDT",
            "timestamp_ms": (index + 1) * 1000,
            "price": price,
            "action": "BUY" if index % 4 else "SELL",
            "confluence_score": 0.25 + (index % 4) * 0.20,
            "confluence_confidence": 0.35 + (index % 4) * 0.20,
            "regime": "TREND" if index % 3 else "RANGE",
        })
    return rows


def test_discovery_selects_on_train_and_evaluates_selected_candidate_oos():
    result = discover_strategy(
        _states(), horizon_ms=1000, cost_bps=2.0,
        min_train_samples=10, monte_carlo_iterations=100,
    )
    assert result["status"] in {"OOS_EVALUATED", "INSUFFICIENT_OOS_DATA"}
    assert result["selection_method"] == "TRAIN_ONLY_GRID_SEARCH_WITH_PURGED_FORWARD_LABELS"
    assert result["candidate_count"] == 9
    assert result["eligible_candidate_count"] >= 1
    assert result["split"]["training_signal_end_ms"] < result["split"]["oos_start_ms"]
    assert result["safety"]["parameters_applied_to_runtime"] is False
    assert result["safety"]["real_authorized"] is False


def test_discovery_fails_closed_when_training_sample_is_too_small():
    result = discover_strategy(
        _states(30), horizon_ms=5000, min_train_samples=100,
        monte_carlo_iterations=50,
    )
    assert result["status"] == "INSUFFICIENT_DATA"
    assert result["orders_submitted"] is False


def test_discovery_rejects_invalid_thresholds():
    try:
        discover_strategy(_states(), confidence_grid=(1.5,))
    except ValueError as exc:
        assert "thresholds" in str(exc)
    else:
        raise AssertionError("invalid candidate threshold was accepted")
