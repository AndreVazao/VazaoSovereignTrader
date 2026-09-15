from PC_ENGINE.core.fast_path import FastPathSignal
from PC_ENGINE.radar.fast_path_bridge import FastPathWebSocketBridge
from PC_ENGINE.radar.websocket_radar import MarketEvent


def _event(price_before=100.0, price=101.0):
    return MarketEvent(
        exchange="okx",
        symbol="BTC/USDT",
        price=price,
        quantity=1.0,
        side="BUY",
        exchange_ts_ms=1000,
        local_ts_ms=1000,
        local_receive_latency_ms=0,
        price_before=price_before,
    )


def test_bridge_disabled_never_routes():
    bridge = FastPathWebSocketBridge({"enabled": False})
    result = bridge.on_market_event(_event())
    assert result.routed is False
    assert result.result is None


def test_bridge_routes_paper_event_after_validated_signal():
    signal = FastPathSignal("BTC/USDT", "binance", "okx", "UP", 1000, 8.0, 0.9, 100)
    calls = []
    bridge = FastPathWebSocketBridge(
        {"enabled": True},
        signals=[signal],
        risk_check=lambda *_: calls.append("risk") or True,
        authorize=lambda *_: calls.append("authorize") or (True, "ok"),
        order=lambda *_: calls.append("order") or type(
            "Order", (), {"ok": True, "reason": "paper fill", "order_id": "p1", "qty": 1.0, "price": 101.0}
        )(),
    )
    result = bridge.on_market_event(_event())
    assert result.routed is True
    assert result.result is not None
    assert result.result.execution.accepted is True
    assert calls == ["risk", "authorize", "order"]


def test_bridge_ignores_first_tick_without_previous_price():
    bridge = FastPathWebSocketBridge({"enabled": True})
    result = bridge.on_market_event(_event(price_before=None, price=101.0))
    assert result.routed is False
