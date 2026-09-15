from __future__ import annotations

from dataclasses import dataclass
from time import time_ns
from typing import Callable, Mapping, Sequence

from PC_ENGINE.core.fast_path import FastPathSignal
from PC_ENGINE.core.fast_path_router import FastPathRouteResult, FastPathRouter
from PC_ENGINE.radar.lead_lag_signal import LeadLagSignalEngine
from PC_ENGINE.radar.websocket_radar import MarketEvent, WebSocketMarketRadar


@dataclass(frozen=True)
class FastPathBridgeResult:
    routed: bool
    result: FastPathRouteResult | None


class FastPathWebSocketBridge:
    """Connect public WebSocket events to the deterministic fast path."""

    def __init__(
        self,
        settings: Mapping[str, object],
        *,
        data_dir: str = "PC_ENGINE/data/radar",
        signals: Sequence[FastPathSignal] | None = None,
        risk_check: Callable[[FastPathSignal, Mapping[str, object]], bool] | None = None,
        authorize: Callable[[object, Mapping[str, object]], tuple[bool, str]] | None = None,
        order: Callable[[object, Mapping[str, object]], object] | None = None,
    ) -> None:
        self.settings = dict(settings)
        self.router = FastPathRouter(self.settings)
        self.data_dir = data_dir
        self._signals = tuple(signals) if signals is not None else None
        self.risk_check = risk_check
        self.authorize = authorize
        self.order = order
        self.last_result: FastPathBridgeResult | None = None

    def load_signals(self) -> tuple[FastPathSignal, ...]:
        if self._signals is None:
            min_confidence = float(self.settings.get("min_confidence", 0.75))
            rows = LeadLagSignalEngine(self.data_dir).signals(min_confidence=min_confidence)
            self._signals = tuple(
                FastPathSignal(
                    symbol=row.symbol,
                    leader=row.leader,
                    follower=row.follower,
                    direction=row.direction,
                    horizon_ms=row.horizon_ms,
                    expectancy_bps=row.expectancy_bps,
                    confidence=row.confidence,
                    samples=row.samples,
                )
                for row in rows
                if row.paper_only
            )
        return self._signals

    @staticmethod
    def _event_mapping(event: MarketEvent) -> dict[str, object] | None:
        if event.price_before is None or event.price_before <= 0:
            return None
        move = event.price - event.price_before
        direction = "UP" if move > 0 else "DOWN" if move < 0 else ""
        if not direction:
            return None
        return {
            "exchange": event.exchange,
            "symbol": event.symbol,
            "price": event.price,
            "quantity": event.quantity,
            "side": event.side,
            "direction": direction,
            "timestamp_ms": event.local_ts_ms,
            "exchange_ts_ms": event.exchange_ts_ms,
            "receive_latency_ms": event.local_receive_latency_ms,
        }

    def on_market_event(self, event: MarketEvent) -> FastPathBridgeResult:
        if not bool(self.settings.get("enabled", False)):
            result = FastPathBridgeResult(False, None)
            self.last_result = result
            return result

        payload = self._event_mapping(event)
        if payload is None:
            result = FastPathBridgeResult(False, None)
            self.last_result = result
            return result

        result = self.router.route(
            payload,
            self.load_signals(),
            now_ms=time_ns() // 1_000_000,
            mode="PAPER",
            risk_check=self.risk_check,
            authorize=self.authorize,
            order=self.order,
        )
        wrapped = FastPathBridgeResult(True, result)
        self.last_result = wrapped
        return wrapped

    def callback(self) -> Callable[[MarketEvent], None]:
        return self.on_market_event

    def build_radar(self, symbols: list[str], exchanges: list[str] | None = None) -> WebSocketMarketRadar:
        radar_settings = self.settings.get("radar", {})
        if not isinstance(radar_settings, Mapping):
            radar_settings = {}
        return WebSocketMarketRadar(
            symbols=symbols,
            exchanges=exchanges,
            data_dir=self.data_dir,
            min_move_bps=float(radar_settings.get("min_move_bps", 5.0)),
            lead_window_ms=int(radar_settings.get("lead_window_ms", 750)),
            callback=self.callback(),
        )
