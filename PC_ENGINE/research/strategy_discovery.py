from __future__ import annotations

from typing import Any

from PC_ENGINE.research.paper_study import _summary, monte_carlo, simulate


def discover_strategy(
    states: list[dict[str, Any]],
    *,
    horizon_ms: int = 5000,
    cost_bps: float = 28.0,
    confidence_grid: tuple[float, ...] = (0.50, 0.65, 0.80),
    confluence_grid: tuple[float, ...] = (0.20, 0.40, 0.60),
    min_train_samples: int = 20,
    monte_carlo_iterations: int = 2000,
) -> dict[str, Any]:
    """Select simple signal filters on a purged training window, then test once OOS.

    Candidate parameters are selected exclusively on training signals. Training
    labels whose forward horizon crosses the OOS boundary are excluded. The OOS
    segment is evaluated once after selection and is never used to rank candidates.
    This is research tooling, not an optimizer connected to live execution.
    """
    if horizon_ms <= 0 or cost_bps < 0:
        raise ValueError("horizon_ms must be positive and cost_bps non-negative")
    if min_train_samples < 1 or monte_carlo_iterations < 1:
        raise ValueError("sample and iteration limits must be positive")
    if not states:
        return {
            "schema_version": 1,
            "status": "INSUFFICIENT_DATA",
            "reason": "no_market_states",
            "paper_only": True,
            "orders_submitted": False,
            "candidate_count": 0,
        }

    ordered = sorted(states, key=lambda row: int(row["timestamp_ms"]))
    unique_times = sorted({int(row["timestamp_ms"]) for row in ordered})
    if len(unique_times) < 3:
        return {
            "schema_version": 1,
            "status": "INSUFFICIENT_DATA",
            "reason": "not_enough_distinct_timestamps",
            "paper_only": True,
            "orders_submitted": False,
            "candidate_count": 0,
        }

    boundary_index = max(1, min(len(unique_times) - 1, int(len(unique_times) * 0.70)))
    oos_start_ms = unique_times[boundary_index]
    train_signal_end_ms = oos_start_ms - int(horizon_ms)
    if train_signal_end_ms <= unique_times[0]:
        return {
            "schema_version": 1,
            "status": "INSUFFICIENT_DATA",
            "reason": "purged_training_window_empty",
            "paper_only": True,
            "orders_submitted": False,
            "candidate_count": 0,
        }

    candidates: list[dict[str, Any]] = []
    for confidence in confidence_grid:
        for confluence in confluence_grid:
            if not 0.0 <= float(confidence) <= 1.0 or not 0.0 <= float(confluence) <= 1.0:
                raise ValueError("candidate thresholds must be between zero and one")
            outcomes = simulate(
                ordered,
                horizon_ms=horizon_ms,
                cost_bps=cost_bps,
                min_confidence=float(confidence),
                min_confluence=float(confluence),
                signal_start_ms=unique_times[0],
                signal_end_ms=train_signal_end_ms,
            )
            # Irregular market observations can resolve a target horizon after
            # the OOS boundary; purge by the actual future observation timestamp.
            outcomes = [
                row for row in outcomes
                if int(row["outcome_timestamp_ms"]) <= oos_start_ms
            ]
            summary = _summary([float(row["net_bps"]) for row in outcomes])
            candidates.append({
                "min_confidence": float(confidence),
                "min_confluence": float(confluence),
                "training": summary,
                "eligible": summary["samples"] >= min_train_samples,
            })

    eligible = [candidate for candidate in candidates if candidate["eligible"]]
    if not eligible:
        return {
            "schema_version": 1,
            "status": "INSUFFICIENT_DATA",
            "reason": "no_candidate_met_minimum_training_samples",
            "paper_only": True,
            "orders_submitted": False,
            "candidate_count": len(candidates),
            "candidates": candidates,
            "split": {
                "oos_start_ms": oos_start_ms,
                "training_signal_end_ms": train_signal_end_ms,
                "purge_horizon_ms": int(horizon_ms),
            },
        }

    # Deterministic tie-breakers prevent arbitrary candidate selection.
    selected = max(
        eligible,
        key=lambda candidate: (
            float(candidate["training"]["mean_net_bps"]),
            int(candidate["training"]["samples"]),
            -float(candidate["min_confidence"]),
            -float(candidate["min_confluence"]),
        ),
    )
    selected_train_outcomes = simulate(
        ordered,
        horizon_ms=horizon_ms,
        cost_bps=cost_bps,
        min_confidence=selected["min_confidence"],
        min_confluence=selected["min_confluence"],
        signal_start_ms=unique_times[0],
        signal_end_ms=train_signal_end_ms,
    )
    selected_train_outcomes = [
        row for row in selected_train_outcomes
        if int(row["outcome_timestamp_ms"]) <= oos_start_ms
    ]
    oos_outcomes = simulate(
        ordered,
        horizon_ms=horizon_ms,
        cost_bps=cost_bps,
        min_confidence=selected["min_confidence"],
        min_confluence=selected["min_confluence"],
        signal_start_ms=oos_start_ms,
    )
    baseline_oos = simulate(
        ordered,
        horizon_ms=horizon_ms,
        cost_bps=cost_bps,
        signal_start_ms=oos_start_ms,
    )
    return {
        "schema_version": 1,
        "status": "OOS_EVALUATED" if oos_outcomes else "INSUFFICIENT_OOS_DATA",
        "paper_only": True,
        "orders_submitted": False,
        "selection_method": "TRAIN_ONLY_GRID_SEARCH_WITH_PURGED_FORWARD_LABELS",
        "candidate_count": len(candidates),
        "eligible_candidate_count": len(eligible),
        "selected_candidate": {
            "min_confidence": selected["min_confidence"],
            "min_confluence": selected["min_confluence"],
            "training": selected["training"],
            "training_max_outcome_timestamp_ms": max(
                (int(row["outcome_timestamp_ms"]) for row in selected_train_outcomes),
                default=0,
            ),
        },
        "oos_selected_candidate": _summary([float(row["net_bps"]) for row in oos_outcomes]),
        "oos_baseline": _summary([float(row["net_bps"]) for row in baseline_oos]),
        "oos_monte_carlo": monte_carlo(
            oos_outcomes, iterations=monte_carlo_iterations, seed=47
        ),
        "candidates": candidates,
        "split": {
            "oos_start_ms": oos_start_ms,
            "training_signal_end_ms": train_signal_end_ms,
            "purge_horizon_ms": int(horizon_ms),
        },
        "safety": {
            "paper_only": True,
            "orders_submitted": False,
            "parameters_applied_to_runtime": False,
            "candidate_promoted": False,
            "real_authorized": False,
        },
    }
