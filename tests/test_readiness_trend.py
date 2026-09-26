from PC_ENGINE.core.readiness_trend import ReadinessTrendEngine


def _rows(pattern, start=1_000_000, step=60_000):
    return [
        {"timestamp_ms": start + i * step, "ready": ready, "status": "READY" if ready else "LOCKED", "blockers": [] if ready else ["X"]}
        for i, ready in enumerate(pattern)
    ]


def test_trend_requires_minimum_history():
    result = ReadinessTrendEngine(min_samples=4, min_span_seconds=1).analyze(_rows([True, True, True]))
    assert result.status == "INSUFFICIENT_HISTORY"


def test_trend_detects_stable_continuous_readiness():
    result = ReadinessTrendEngine(min_samples=5, recent_window=3, min_span_seconds=1).analyze(_rows([True] * 6))
    assert result.status == "STABLE"
    assert result.consecutive_ready == 6
    assert result.recent_ready_ratio == 1.0


def test_trend_detects_degradation():
    result = ReadinessTrendEngine(min_samples=6, recent_window=3, min_span_seconds=1).analyze(_rows([True, True, True, True, False, False, False]))
    assert result.status == "DEGRADING"
    assert result.degradation_ratio > 0.2
    assert result.consecutive_blocked == 3


def test_trend_detects_recovery():
    result = ReadinessTrendEngine(min_samples=6, recent_window=3, min_span_seconds=1).analyze(_rows([False, False, False, False, True, True, True]))
    assert result.status == "RECOVERING"
    assert result.improvement_ratio > 0.2


def test_trend_fails_closed_on_malformed_history():
    rows = _rows([True] * 6)
    rows[2]["ready"] = "yes"
    result = ReadinessTrendEngine(min_samples=5, min_span_seconds=1).analyze(rows)
    assert result.status == "INVALID_HISTORY"


def test_trend_rejects_duplicate_timestamps():
    rows = _rows([True] * 6)
    rows[3]["timestamp_ms"] = rows[2]["timestamp_ms"]
    result = ReadinessTrendEngine(min_samples=5, min_span_seconds=1).analyze(rows)
    assert result.status == "INVALID_HISTORY"
