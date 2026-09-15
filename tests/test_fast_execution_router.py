from PC_ENGINE.core.fast_execution_metrics import FastExecutionMetrics
from PC_ENGINE.core.fast_execution_router import FastExecutionRouter
from PC_ENGINE.core.fast_path import FastPathEngine, FastPathSignal


def signal(**overrides):
    values = dict(symbol="BTC/USDT", leader="binance", follower="bingx", direction="UP", horizon_ms=500, expectancy_bps=8.0, confidence=0.9, samples=500)
    values.update(overrides)
    return FastPathSignal(**values)


def event(**overrides):
    values = {"symbol": "BTC/USDT", "exchange": "bingx", "direction": "UP", "exchange_ts_ms": 1000}
    values.update(overrides)
    return values


def test_router_accepts_but_does_not_execute_without_executor():
    router = FastExecutionRouter(FastPathEngine(max_signal_age_ms=1000))
    result = router.handle(event(), (signal(),), now_ms=1050)
    assert result.accepted is True
    assert result.executed is False
    assert result.reason == "executor_not_configured"


def test_router_executes_only_after_risk_check():
    calls = []
    router = FastExecutionRouter(FastPathEngine(), executor=lambda decision, payload: calls.append(payload["exchange"]) or True)
    result = router.handle(event(), (signal(),), now_ms=1050, risk_check=lambda learned, payload: True)
    assert result.accepted is True
    assert result.executed is True
    assert calls == ["bingx"]


def test_router_cannot_bypass_risk_rejection():
    calls = []
    router = FastExecutionRouter(FastPathEngine(), executor=lambda decision, payload: calls.append(True) or True)
    result = router.handle(event(), (signal(),), now_ms=1050, risk_check=lambda learned, payload: False)
    assert result.accepted is False
    assert result.executed is False
    assert result.reason == "risk_rejected"
    assert calls == []


def test_router_rejects_stale_event_without_executor_call():
    calls = []
    router = FastExecutionRouter(FastPathEngine(max_signal_age_ms=100), executor=lambda decision, payload: calls.append(True) or True)
    result = router.handle(event(), (signal(),), now_ms=1201)
    assert result.accepted is False
    assert result.reason == "stale_event"
    assert calls == []


def test_router_records_metrics():
    metrics = FastExecutionMetrics()
    router = FastExecutionRouter(FastPathEngine(), metrics=metrics)
    router.handle(event(), (signal(),), now_ms=1050)
    snapshot = metrics.snapshot()
    assert snapshot.evaluations == 1
    assert snapshot.accepted == 1
    assert snapshot.executed == 0
    assert snapshot.max_latency_ns >= 0
