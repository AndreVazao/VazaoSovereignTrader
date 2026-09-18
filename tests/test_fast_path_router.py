from PC_ENGINE.core.fast_path import FastPathSignal
from PC_ENGINE.core.fast_path_router import FastPathRouter


def test_router_stays_observation_only_when_disabled():
    router = FastPathRouter({"enabled": False})
    signal = FastPathSignal("BTC/USDT", "binance", "okx", "UP", 1000, 8.0, 0.9, 100)
    result = router.route(
        {"symbol": "BTC/USDT", "exchange": "okx", "direction": "UP", "timestamp_ms": 1000},
        [signal], now_ms=1010, mode="PAPER",
        risk_check=lambda *_: True,
        authorize=lambda *_: (True, "ok"),
        order=lambda *_: (_ for _ in ()).throw(AssertionError("order must not run")),
    )
    assert result.decision_reason == "validated_fast_path"
    assert result.execution.reason == "fast_path_disabled"


def test_router_authorizes_and_executes_paper():
    router = FastPathRouter({"enabled": True})
    signal = FastPathSignal("BTC/USDT", "binance", "okx", "UP", 1000, 8.0, 0.9, 100)
    result = router.route(
        {"symbol": "BTC/USDT", "exchange": "okx", "direction": "UP", "timestamp_ms": 1000},
        [signal], now_ms=1010, mode="PAPER",
        risk_check=lambda *_: True,
        authorize=lambda *_: (True, "risk ok"),
        order=lambda *_: type("Order", (), {"ok": True, "reason": "paper fill", "order_id": "p1", "qty": 1.0, "price": 100.0})(),
    )
    assert result.execution.accepted
    assert result.execution.order_id == "p1"
    assert router.metrics.snapshot()["execution_successes"] == 1
