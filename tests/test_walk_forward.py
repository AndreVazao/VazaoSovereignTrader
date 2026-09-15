from __future__ import annotations

import json
from pathlib import Path

from PC_ENGINE.core.walk_forward import WalkForwardEvaluator


def _write_rows(path: Path, values: list[float]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for i, value in enumerate(values):
            handle.write(json.dumps({
                "ts_ms": i,
                "evaluated_ts_ms": i,
                "symbol": "BTC/USDT",
                "action": "BUY",
                "horizon_ms": 5000,
                "net_bps": value,
            }) + "\n")


def test_walk_forward_passes_on_strong_out_of_sample_edge(tmp_path: Path) -> None:
    data_dir = tmp_path / "radar"
    data_dir.mkdir()
    _write_rows(data_dir / "confluence_outcomes.jsonl", [1.0] * 70 + [2.0] * 30)
    evaluator = WalkForwardEvaluator(data_dir=data_dir, min_train_samples=50, min_validation_samples=20)
    result = evaluator.evaluate()
    assert result["results"][0]["passed"] is True


def test_walk_forward_rejects_negative_validation(tmp_path: Path) -> None:
    data_dir = tmp_path / "radar"
    data_dir.mkdir()
    _write_rows(data_dir / "confluence_outcomes.jsonl", [2.0] * 70 + [-2.0] * 30)
    evaluator = WalkForwardEvaluator(data_dir=data_dir, min_train_samples=50, min_validation_samples=20)
    result = evaluator.evaluate()
    assert result["results"][0]["passed"] is False
    assert "validation_expectancy_not_positive" in result["results"][0]["reason"]
