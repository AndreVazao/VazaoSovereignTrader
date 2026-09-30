# Path: tests/test_execution_gate_live_quality.py
from PC_ENGINE.core.engine import SovereignEngine


def _engine():
    engine = SovereignEngine.__new__(SovereignEngine)
    engine.config = {"market_data_quality": {"max_ticker_age_seconds": 5}}
    return engine


def test_real_execution_ticker_requires_timestamp():
    engine = _engine()
    assert not engine._ticker_is_fresh({"last": 100.0}, now_ms=10_000)


def test_real_execution_ticker_rejects_stale_timestamp():
    engine = _engine()
    assert not engine._ticker_is_fresh({"timestamp": 4_000}, now_ms=10_000)


def test_real_execution_ticker_accepts_recent_timestamp():
    engine = _engine()
    assert engine._ticker_is_fresh({"timestamp": 9_000}, now_ms=10_000)


def test_real_execution_ticker_rejects_unreasonable_future_timestamp():
    engine = _engine()
    assert not engine._ticker_is_fresh({"timestamp": 13_000}, now_ms=10_000)
