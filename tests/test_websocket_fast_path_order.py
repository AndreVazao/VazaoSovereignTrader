from PC_ENGINE.radar.websocket_radar import MarketEvent, WebSocketMarketRadar


def test_callback_runs_before_persistence(tmp_path):
    events = []
    radar = WebSocketMarketRadar(
        symbols=["BTC/USDT"],
        exchanges=["binance"],
        data_dir=tmp_path,
        callback=lambda event: events.append("callback"),
    )
    radar._persist = lambda event: events.append("persist")
    radar._emit(
        MarketEvent(
            exchange="binance",
            symbol="BTC/USDT",
            price=101.0,
            quantity=1.0,
            side="BUY",
            exchange_ts_ms=1000,
            local_ts_ms=1001,
            local_receive_latency_ms=1,
            price_before=100.0,
        )
    )
    assert events == ["callback", "persist"]
