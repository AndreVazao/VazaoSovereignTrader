from __future__ import annotations

import threading
import time
from typing import Callable

from PC_ENGINE.core.candlestick_patterns import CandlestickPatternEngine
from PC_ENGINE.core.confluence_runtime import PaperConfluenceRuntime
from PC_ENGINE.radar.market_radar import MarketRadar


class PaperMarketCollector:
    """Continuous PAPER-only market-state collector.

    Collects public cross-exchange observations and feeds the existing
    confluence/state pipeline. It never submits orders and never changes
    trading mode.
    """

    def __init__(
        self,
        settings: dict,
        symbols: list[str],
        ohlcv_fetcher: Callable[[str, str, int], list[list[float]]],
        strategy,
        on_error: Callable[[str, dict], None] | None = None,
    ) -> None:
        self.settings = settings
        self.symbols = list(dict.fromkeys(symbols))
        self.ohlcv_fetcher = ohlcv_fetcher
        self.strategy = strategy
        self.on_error = on_error
        self.interval_seconds = max(2.0, float(settings.get("interval_seconds", 5.0)))
        self.timeframe = str(settings.get("timeframe", "1m"))
        self.candles_limit = max(30, int(settings.get("candles_limit", 120)))
        self.radar = MarketRadar(
            exchanges=settings.get(
                "polling_exchanges",
                ["binance", "bingx", "okx", "bybit", "coinbase"],
            ),
            symbols=self.symbols,
            data_dir=settings.get("data_dir", "PC_ENGINE/data/radar"),
        )
        self.confluence = PaperConfluenceRuntime(settings.get("confluence", {}))
        self.patterns = CandlestickPatternEngine(settings.get("candlestick", {}))
        self.stop_event = threading.Event()
        self.thread: threading.Thread | None = None
        self.last_cycle_ms = 0
        self.cycles = 0
        self.errors = 0

    def start(self) -> None:
        if self.thread and self.thread.is_alive():
            return
        self.stop_event.clear()
        self.thread = threading.Thread(target=self._loop, name="paper-market-collector", daemon=True)
        self.thread.start()

    def stop(self) -> None:
        self.stop_event.set()
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=max(2.0, self.interval_seconds + 1.0))
        self.radar.close()
        self.thread = None

    def snapshot(self) -> dict:
        return {
            "running": bool(self.thread and self.thread.is_alive()),
            "interval_seconds": self.interval_seconds,
            "cycles": self.cycles,
            "errors": self.errors,
            "last_cycle_ms": self.last_cycle_ms,
            "data_dir": str(self.confluence.data_dir),
        }

    def _report_error(self, message: str, data: dict) -> None:
        self.errors += 1
        if self.on_error:
            self.on_error(message, data)

    def _loop(self) -> None:
        while not self.stop_event.is_set():
            started = time.monotonic()
            try:
                self.collect_once()
            except Exception as exc:
                self._report_error("PAPER_COLLECTOR_ERROR", {"error": str(exc)})
            elapsed = time.monotonic() - started
            self.stop_event.wait(max(0.0, self.interval_seconds - elapsed))

    def collect_once(self) -> int:
        snapshots, _ = self.radar.snapshot()
        prices = {snap.symbol: snap.price for snap in snapshots}
        pressure = self.radar.pressure(snapshots)
        recorded = 0

        for symbol in self.symbols:
            try:
                ohlcv = self.ohlcv_fetcher(symbol, self.timeframe, self.candles_limit)
                if len(ohlcv) < 30:
                    continue
                ticker_price = prices.get(symbol)
                if not ticker_price or ticker_price <= 0:
                    ticker_price = float(ohlcv[-1][4])
                signal = self.strategy.analyse(symbol, ohlcv, 0.0)
                pattern_bias, _, _ = self.patterns.evaluate(ohlcv)
                result = self.confluence.evaluate_and_record(
                    symbol=symbol,
                    price=ticker_price,
                    ohlcv=ohlcv,
                    technical_action=signal.action,
                    technical_strength=float(signal.strength),
                    pattern_bias=pattern_bias,
                    radar_pressure=float(pressure.get(symbol, 0.0)),
                    timeframes={self.timeframe: ohlcv},
                )
                recorded += 1
                if self.on_error and not result.recorded:
                    self.on_error("PAPER_STATE_NOT_RECORDED", {"symbol": symbol})
            except Exception as exc:
                self._report_error("PAPER_SYMBOL_COLLECTION_ERROR", {"symbol": symbol, "error": str(exc)})

        self.confluence.resolve_outcomes()
        self.cycles += 1
        self.last_cycle_ms = int(time.time() * 1000)
        return recorded
