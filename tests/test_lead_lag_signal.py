from __future__ import annotations

import json

import pytest

from PC_ENGINE.radar.lead_lag_signal import LeadLagSignalEngine


def write_stats(tmp_path, rows):
    tmp_path.mkdir(parents=True, exist_ok=True)
    (tmp_path / "lead_lag_learning.json").write_text(
        json.dumps({"stats": rows}), encoding="utf-8"
    )
    return LeadLagSignalEngine(tmp_path)


def valid_row(**overrides):
    row = {
        "eligible": True,
        "symbol": "btc/usdt",
        "leader": " Binance ",
        "follower": "COINBASE",
        "direction": "up",
        "horizon_ms": 250,
        "expectancy_bps": 4.5,
        "confidence": 0.91,
        "samples": 120,
        "regime": "trending",
    }
    row.update(overrides)
    return row


def test_valid_learned_signal_is_normalized_and_remains_paper_only(tmp_path):
    engine = write_stats(tmp_path, [valid_row()])

    signals = engine.signals()

    assert len(signals) == 1
    signal = signals[0]
    assert signal.symbol == "BTC/USDT"
    assert signal.leader == "binance"
    assert signal.follower == "coinbase"
    assert signal.direction == "UP"
    assert signal.regime == "TRENDING"
    assert signal.paper_only is True


@pytest.mark.parametrize(
    "row",
    [
        valid_row(eligible="true"),
        valid_row(confidence=float("nan")),
        valid_row(confidence=1.5),
        valid_row(expectancy_bps=float("inf")),
        valid_row(samples=0),
        valid_row(horizon_ms=1.5),
        valid_row(symbol=" "),
        valid_row(leader="binance", follower=" BINANCE "),
        valid_row(direction="SIDEWAYS"),
        {"eligible": True, "confidence": 0.99},
    ],
)
def test_malformed_or_unsafe_learning_rows_are_ignored(tmp_path, row):
    engine = write_stats(tmp_path, [row])

    assert engine.signals() == []


@pytest.mark.parametrize("threshold", [float("nan"), float("inf"), -0.01, 1.01, "bad"])
def test_invalid_minimum_confidence_is_rejected(tmp_path, threshold):
    engine = write_stats(tmp_path, [valid_row()])

    with pytest.raises(ValueError, match="min_confidence"):
        engine.signals(min_confidence=threshold)


def test_missing_or_invalid_learning_file_fails_closed(tmp_path):
    engine = LeadLagSignalEngine(tmp_path)
    assert engine.signals() == []

    (tmp_path / "lead_lag_learning.json").write_text("{broken", encoding="utf-8")
    assert engine.signals() == []
