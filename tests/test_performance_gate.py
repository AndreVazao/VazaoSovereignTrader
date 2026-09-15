from pathlib import Path

from PC_ENGINE.core.performance_gate import PerformanceGate


def _write(path: Path, rows: list[dict]) -> None:
    import json
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")


def test_learning_mode_before_minimum(tmp_path: Path):
    gate = PerformanceGate(tmp_path, min_samples=3)
    _write(tmp_path / "confluence_outcomes.jsonl", [
        {"symbol": "BTC/USDT", "action": "BUY", "horizon_ms": 15000, "net_bps": 5},
    ])
    result = gate.evaluate("BTC/USDT", "BUY", 15000)
    assert result.status == "LEARNING"
    assert result.eligible is True


def test_validated_positive_expectancy(tmp_path: Path):
    gate = PerformanceGate(tmp_path, min_samples=3, min_win_rate=0.5)
    _write(tmp_path / "confluence_outcomes.jsonl", [
        {"symbol": "BTC/USDT", "action": "BUY", "horizon_ms": 15000, "net_bps": 8},
        {"symbol": "BTC/USDT", "action": "BUY", "horizon_ms": 15000, "net_bps": 9},
        {"symbol": "BTC/USDT", "action": "BUY", "horizon_ms": 15000, "net_bps": 10},
    ])
    result = gate.evaluate("BTC/USDT", "BUY", 15000)
    assert result.status == "VALIDATED"
    assert result.eligible is True


def test_rejected_negative_expectancy(tmp_path: Path):
    gate = PerformanceGate(tmp_path, min_samples=3)
    _write(tmp_path / "confluence_outcomes.jsonl", [
        {"symbol": "BTC/USDT", "action": "BUY", "horizon_ms": 15000, "net_bps": -8},
        {"symbol": "BTC/USDT", "action": "BUY", "horizon_ms": 15000, "net_bps": -9},
        {"symbol": "BTC/USDT", "action": "BUY", "horizon_ms": 15000, "net_bps": -10},
    ])
    result = gate.evaluate("BTC/USDT", "BUY", 15000)
    assert result.status == "REJECTED"
    assert result.eligible is False
