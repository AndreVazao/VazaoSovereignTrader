import json
from pathlib import Path

from PC_ENGINE.radar.websocket_radar import MarketEvent, WebSocketMarketRadar


def test_websocket_events_are_persisted_flat(tmp_path: Path):
    radar = WebSocketMarketRadar(["BTC/USDT"], exchanges=[], data_dir=tmp_path)
    event = MarketEvent("binance", "BTC/USDT", 100.0, 1.0, "BUY", 1000, 1001, 1)
    radar._persist(event)
    row = json.loads((tmp_path / "websocket_events.jsonl").read_text())
    assert row["symbol"] == "BTC/USDT"
    assert "event" not in row
