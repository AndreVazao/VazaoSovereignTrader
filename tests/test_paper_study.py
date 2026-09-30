from __future__ import annotations

from PC_ENGINE.research.paper_study import (
    compare_paper_policies,
    monte_carlo,
    run_study,
    simulate,
)


def _states():
    prices = [100, 101, 102, 101, 103, 104, 103, 105, 106, 105, 107, 108]
    rows = []
    for i, price in enumerate(prices):
        rows.append({
            "symbol": "BTC/USDT",
            "timestamp_ms": i * 1000,
            "price": price,
            "regime": "TREND" if i < 8 else "RANGE",
            "action": "BUY" if i % 3 else "SELL",
            "confluence_score": 0.8 if i % 2 else 0.2,
            "confluence_confidence": 0.9 if i % 2 else 0.6,
        })
    return rows


def test_simulate_is_paper_only_and_net_of_costs():
    rows = simulate(_states(), horizon_ms=2000, cost_bps=10)
    assert rows
    assert all("net_bps" in row for row in rows)


def test_walk_forward_and_oos_are_chronological():
    report = run_study(_states(), horizon_ms=1000, cost_bps=10, folds=3, min_train=4, test_size=2, monte_carlo_iterations=100)
    assert report["paper_only"] is True
    assert report["orders_submitted"] is False
    assert report["chronological_oos"]["train"]["samples"] > 0
    assert report["chronological_oos"]["test"]["samples"] > 0
    assert all(fold["test_start_ms"] <= fold["test_end_ms"] for fold in report["walk_forward"])


def test_regime_breakdown_and_policy_comparison_are_present():
    report = run_study(_states(), horizon_ms=1000, cost_bps=10, monte_carlo_iterations=50)
    assert "TREND" in report["regimes"]
    assert "RANGE" in report["regimes"]
    comparison = compare_paper_policies(_states(), horizon_ms=1000, cost_bps=10)
    assert comparison["high_confidence"]["samples"] <= comparison["signal"]["samples"]


def test_monte_carlo_is_reproducible():
    rows = simulate(_states(), horizon_ms=1000, cost_bps=10)
    a = monte_carlo(rows, iterations=100, seed=42)
    b = monte_carlo(rows, iterations=100, seed=42)
    assert a == b
