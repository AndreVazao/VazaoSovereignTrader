from PC_ENGINE.core.fast_path import FastPathSignal
from PC_ENGINE.core.fast_path_router import FastPathRouter


def test_router_disabled_is_safe():
    router = FastPathRouter({"enabled": False})
    signal = FastPathSignal("BTC/USDT", "binance", "okx", "UP", 1000, 8.0, 0.9, 100)
    result = router.route(
        {"symbol": "BTC/USDT", "exchange": "okx", "direction": "UP", "timestamp_ms": 1000},
        [signal], now_ms=1010, mode="PAPER",
        risk_check=lambda *_: True,
        authorize=lambda *_: (True, "ok"),
        order=lambda *_: (_ for _ in ()).throw(AssertionError("order must not run")),
    )
    assert result.execution.reason == "fast_path_disabled"
