from __future__ import annotations

from pathlib import Path

from PC_ENGINE.core.strategy import Signal
from PC_ENGINE.services.paper_market_collector import PaperMarketCollector


class FakeStrategy:
    def analyse(self, symbol, ohlcv, spread_pct=0.0):
        return Signal("BUY", "TREND_UP", 0.8, "test", 0.01, 0.02)


def _ohlcv(count: int = 40):
    rows = []
    price = 100.0
    for i in range(count):
        price += 0.2
        rows.append([i * 60_000, price - 0.1, price + 0.2, price - 0.2, price, 1000.0])
    return rows


def test_collector_records_market_state(tmp_path: Path):
    settings = {
        "interval_seconds": 5,
        "polling_exchanges": [],
        "data_dir": str(tmp_path),
        "candlestick": {"enabled": True, "min_confidence": 0.70},
        "confluence": {
            "enabled": True,
            "observational_only": True,
            "paper_only": True,
            "data_dir": str(tmp_path),
            "derivatives": {"enabled": False, "observational_only": True},
        },
    }

    collector = PaperMarketCollector(
        settings=settings,
        symbols=["BTC/USDT"],
        ohlcv_fetcher=lambda symbol, timeframe, limit: _ohlcv(),
        strategy=FakeStrategy(),
    )
    try:
        recorded = collector.collect_once()
        assert recorded == 1
        state_path = tmp_path / "market_states.jsonl"
        assert state_path.exists()
        assert '"symbol":"BTC/USDT"' in state_path.read_text(encoding="utf-8")
        assert collector.snapshot()["cycles"] == 1
    finally:
        collector.stop()


def test_collector_never_uses_order_interface(tmp_path: Path):
    settings = {
        "polling_exchanges": [],
        "data_dir": str(tmp_path),
        "confluence": {
            "data_dir": str(tmp_path),
            "derivatives": {"enabled": False, "observational_only": True},
        },
    }
    calls = []

    collector = PaperMarketCollector(
        settings=settings,
        symbols=["BTC/USDT"],
        ohlcv_fetcher=lambda symbol, timeframe, limit: _ohlcv(),
        strategy=FakeStrategy(),
    )
    try:
        collector.collect_once()
        assert calls == []
    finally:
        collector.stop()
