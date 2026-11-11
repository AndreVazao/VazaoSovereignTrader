from __future__ import annotations

import json

import pytest

from PC_ENGINE.research.strategy_advisor import assess_strategy_report, write_advisor_report


def _study(*, positive: bool = True) -> dict:
    mean = 8.0 if positive else -4.0
    return {
        "paper_only": True,
        "orders_submitted": False,
        "overall": {"samples": 160, "mean_net_bps": mean},
        "chronological_oos": {
            "train": {"samples": 100, "mean_net_bps": mean},
            "test": {"samples": 60, "mean_net_bps": mean},
        },
        "walk_forward": [
            {"test_summary": {"samples": 20, "mean_net_bps": mean}}
            for _ in range(5)
        ],
        "monte_carlo": {"probability_mean_leq_zero": 0.08 if positive else 0.92},
        "regimes": {
            "UP_LOW": {"samples": 40, "mean_net_bps": mean},
            "RANGE_NORMAL": {"samples": 30, "mean_net_bps": 2.0 if positive else -2.0},
        },
    }


def test_promising_study_is_only_recommended_for_more_paper_research():
    result = assess_strategy_report(_study())
    assert result["decision"] == "CONTINUE_PAPER_RESEARCH"
    assert result["safety"]["paper_only"] is True
    assert result["safety"]["candidate_promoted"] is False
    assert result["safety"]["real_authorized"] is False


def test_negative_oos_and_monte_carlo_are_rejected():
    result = assess_strategy_report(_study(positive=False))
    assert result["decision"] == "REJECT_OR_REWORK"
    assert result["gates"]["positive_oos_net_expectancy"] is False
    assert result["gates"]["monte_carlo_uncertainty"] is False


def test_small_sample_is_insufficient_not_a_success():
    study = _study()
    study["overall"]["samples"] = 12
    study["chronological_oos"]["test"]["samples"] = 4
    result = assess_strategy_report(study)
    assert result["decision"] == "INSUFFICIENT_EVIDENCE"


def test_non_paper_report_is_refused():
    study = _study()
    study["orders_submitted"] = True
    with pytest.raises(ValueError):
        assess_strategy_report(study)


def test_missing_monte_carlo_is_fail_closed():
    study = _study()
    study.pop("monte_carlo")
    result = assess_strategy_report(study)
    assert result["gates"]["monte_carlo_uncertainty"] is False


def test_report_is_written_atomically(tmp_path):
    path = tmp_path / "advisor.json"
    payload = assess_strategy_report(_study())
    write_advisor_report(payload, path)
    loaded = json.loads(path.read_text(encoding="utf-8"))
    assert loaded["advisor"] == "VST_PAPER_STRATEGY_ADVISOR"
    assert not path.with_suffix(".json.tmp").exists()
