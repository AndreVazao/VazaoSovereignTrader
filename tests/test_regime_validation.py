from __future__ import annotations

import json
from pathlib import Path

from PC_ENGINE.core.regime_validation import RegimeAwareValidator


def _write(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")


def test_regime_validation_separates_regimes(tmp_path: Path) -> None:
    data_dir = tmp_path / "radar"
    data_dir.mkdir()
    rows = []
    rows += [{"symbol": "BTC/USDT", "action": "BUY", "horizon_ms": 5000, "regime": "UP_LOW", "net_bps": 2.0}] * 35
    rows += [{"symbol": "BTC/USDT", "action": "BUY", "horizon_ms": 5000, "regime": "DOWN_HIGH", "net_bps": -2.0}] * 35
    _write(data_dir / "confluence_outcomes.jsonl", rows)
    result = RegimeAwareValidator(data_dir=data_dir, min_samples=30).evaluate()
    by_regime = {row["regime"]: row for row in result["results"]}
    assert by_regime["UP_LOW"]["passed"] is True
    assert by_regime["DOWN_HIGH"]["passed"] is False
