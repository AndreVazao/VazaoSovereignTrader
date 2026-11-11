from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any


def _number(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if math.isfinite(number) else default


def _count(summary: Any) -> int:
    if not isinstance(summary, dict):
        return 0
    try:
        return max(0, int(summary.get("samples", 0)))
    except (TypeError, ValueError):
        return 0


def assess_strategy_report(
    report: dict[str, Any],
    *,
    min_outcomes: int = 100,
    min_oos_samples: int = 30,
    min_regime_samples: int = 20,
    min_positive_fold_ratio: float = 0.60,
    max_probability_non_positive: float = 0.25,
) -> dict[str, Any]:
    """Convert a PAPER study into conservative, explainable research guidance.

    This function never changes strategy parameters, promotes candidates, adjusts
    risk, authorizes capital, or submits orders. It requires an explicit PAPER
    report and treats missing evidence as insufficient rather than as success.
    """
    if not isinstance(report, dict):
        raise TypeError("study report must be an object")
    if report.get("paper_only") is not True or report.get("orders_submitted") is not False:
        raise ValueError("strategy advisor accepts PAPER-only reports with no submitted orders")
    if min_outcomes < 1 or min_oos_samples < 1 or min_regime_samples < 1:
        raise ValueError("sample thresholds must be positive")
    if not 0.0 <= min_positive_fold_ratio <= 1.0:
        raise ValueError("min_positive_fold_ratio must be between zero and one")
    if not 0.0 <= max_probability_non_positive <= 1.0:
        raise ValueError("max_probability_non_positive must be between zero and one")

    overall = report.get("overall") if isinstance(report.get("overall"), dict) else {}
    oos = report.get("chronological_oos") if isinstance(report.get("chronological_oos"), dict) else {}
    test = oos.get("test") if isinstance(oos.get("test"), dict) else {}
    monte_carlo = report.get("monte_carlo") if isinstance(report.get("monte_carlo"), dict) else {}
    folds = report.get("walk_forward") if isinstance(report.get("walk_forward"), list) else []
    regimes = report.get("regimes") if isinstance(report.get("regimes"), dict) else {}

    outcome_count = _count(overall)
    oos_count = _count(test)
    oos_mean = _number(test.get("mean_net_bps"))
    probability_non_positive = _number(monte_carlo.get("probability_mean_leq_zero"), 1.0)
    valid_folds = [
        fold for fold in folds
        if isinstance(fold, dict) and isinstance(fold.get("test_summary"), dict)
        and _count(fold["test_summary"]) > 0
    ]
    positive_folds = sum(
        1 for fold in valid_folds
        if _number(fold["test_summary"].get("mean_net_bps")) > 0
    )
    positive_fold_ratio = positive_folds / len(valid_folds) if valid_folds else 0.0

    regime_rows = []
    for name, summary in sorted(regimes.items()):
        if not isinstance(summary, dict):
            continue
        samples = _count(summary)
        regime_rows.append({
            "regime": str(name),
            "samples": samples,
            "mean_net_bps": round(_number(summary.get("mean_net_bps")), 6),
            "evidence_sufficient": samples >= min_regime_samples,
            "research_bias": (
                "PROMISING_TO_INVESTIGATE"
                if samples >= min_regime_samples and _number(summary.get("mean_net_bps")) > 0
                else "WEAK_OR_INSUFFICIENT"
            ),
        })

    gates = {
        "minimum_outcomes": outcome_count >= min_outcomes,
        "minimum_oos_samples": oos_count >= min_oos_samples,
        "positive_oos_net_expectancy": oos_mean > 0,
        "walk_forward_consistency": bool(valid_folds) and positive_fold_ratio >= min_positive_fold_ratio,
        "monte_carlo_uncertainty": probability_non_positive <= max_probability_non_positive,
        "regime_evidence": any(row["evidence_sufficient"] for row in regime_rows),
    }
    if outcome_count < min_outcomes or oos_count < min_oos_samples or not valid_folds:
        decision = "INSUFFICIENT_EVIDENCE"
        rationale = "Amostra OOS ou validação walk-forward insuficiente; continuar a recolher dados PAPER."
    elif all(gates.values()):
        decision = "CONTINUE_PAPER_RESEARCH"
        rationale = "Os gates estatísticos mínimos passaram; manter em investigação PAPER, sem promoção automática."
    else:
        decision = "REJECT_OR_REWORK"
        failed = [name for name, passed in gates.items() if not passed]
        rationale = "Gates por cumprir: " + ", ".join(failed) + ". Rever hipótese, custos e estabilidade antes de novo estudo."

    return {
        "schema_version": 1,
        "advisor": "VST_PAPER_STRATEGY_ADVISOR",
        "decision": decision,
        "rationale": rationale,
        "metrics": {
            "outcomes": outcome_count,
            "oos_samples": oos_count,
            "oos_mean_net_bps": round(oos_mean, 6),
            "walk_forward_folds": len(valid_folds),
            "positive_walk_forward_folds": positive_folds,
            "positive_walk_forward_ratio": round(positive_fold_ratio, 6),
            "monte_carlo_probability_mean_leq_zero": round(probability_non_positive, 6),
        },
        "gates": gates,
        "regimes": regime_rows,
        "thresholds": {
            "min_outcomes": min_outcomes,
            "min_oos_samples": min_oos_samples,
            "min_regime_samples": min_regime_samples,
            "min_positive_fold_ratio": min_positive_fold_ratio,
            "max_probability_non_positive": max_probability_non_positive,
        },
        "safety": {
            "paper_only": True,
            "orders_submitted": False,
            "strategy_parameters_changed": False,
            "candidate_promoted": False,
            "risk_changed": False,
            "real_authorized": False,
        },
    }


def write_advisor_report(payload: dict[str, Any], path: str | Path) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(target)
