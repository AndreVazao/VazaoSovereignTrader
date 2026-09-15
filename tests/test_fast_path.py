from __future__ import annotations

import time

from PC_ENGINE.core.fast_path import FastPathEngine, FastPathSignal, load_fast_signals
from PC_ENGINE.core.slow_learning import SlowLearningQueue


def signal(**overrides):
    values = dict(symbol="BTC/USDT", leader="binance", follower="bingx", direction="UP",
                  horizon_ms=500, expectancy_bps=8.0, confidence=0.9, samples=500)
    values.update(overrides)
    return FastPathSignal(**values)


def test_fast_path_accepts_fresh_validated_signal():
    engine = FastPathEngine()
    decision = engine.evaluate(
        {"symbol": "BTC/USDT", "exchange": "bingx", "direction": "UP", "timestamp_ms": 1000},
        [signal()], now_ms=1050,
        risk_check=lambda *_: True,
    )
    assert decision.accepted is True
    assert decision.reason == "validated_fast_path"
    assert decision.evaluation_ns >= 0


def test_fast_path_rejects_stale_event():
    decision = FastPathEngine(max_signal_age_ms=100).evaluate(
        {"symbol": "BTC/USDT", "exchange": "bingx", "direction": "UP", "timestamp_ms": 1000},
        [signal()], now_ms=1201,
    )
    assert decision.accepted is False
    assert decision.reason == "stale_event"


def test_fast_path_never_bypasses_risk():
    decision = FastPathEngine().evaluate(
        {"symbol": "BTC/USDT", "exchange": "bingx", "direction": "UP", "timestamp_ms": 1000},
        [signal()], now_ms=1010,
        risk_check=lambda *_: False,
    )
    assert decision.accepted is False
    assert decision.reason == "risk_rejected"


def test_load_fast_signals_filters_invalid_and_ineligible_rows():
    rows = [
        {"eligible": True, "symbol": "BTC/USDT", "leader": "binance", "follower": "bingx",
         "direction": "UP", "horizon_ms": 500, "expectancy_bps": 8, "confidence": .9, "samples": 100},
        {"eligible": False},
        {"eligible": True, "symbol": "broken"},
    ]
    loaded = load_fast_signals(rows)
    assert len(loaded) == 1


def test_slow_learning_submit_is_non_blocking_when_full():
    learner = SlowLearningQueue(maxsize=1)
    event = learner.submit_mapping("BTC/USDT", "BUY", 1, {"score": .8})
    dropped = learner.submit_mapping("BTC/USDT", "BUY", 2, {"score": .9})
    assert event is True
    assert dropped is False
    assert learner.dropped == 1


def test_slow_learning_processes_without_blocking_submission(tmp_path):
    learner = SlowLearningQueue(data_dir=tmp_path)
    learner.start()
    assert learner.submit_mapping("BTC/USDT", "BUY", 1, {"score": .8})
    deadline = time.time() + 2
    while time.time() < deadline and learner.processed < 1:
        time.sleep(0.01)
    learner.stop()
    assert learner.processed == 1
    assert (tmp_path / "slow_learning_events.jsonl").exists()
