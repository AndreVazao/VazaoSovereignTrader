from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from PC_ENGINE.core.confluence import ConfluenceEngine, ConfluenceScore
from PC_ENGINE.core.paper_confluence_tracker import PaperConfluenceTracker
from PC_ENGINE.radar.lead_lag_signal import LeadLagSignalEngine
from PC_ENGINE.radar.regime_engine import MarketRegimeEngine


@dataclass(frozen=True)
class ConfluenceRuntimeResult:
    score: ConfluenceScore
    recorded: bool


class PaperConfluenceRuntime:
    """Runtime bridge for PAPER intelligence collection.

    It enriches the existing strategy signal with learned lead/lag evidence,
    evaluates confluence and records the observation. It never sends orders.
    """

    def __init__(self, settings: dict | None = None):
        settings = settings or {}
        self.engine = ConfluenceEngine(settings)
        self.tracker = PaperConfluenceTracker(
            data_dir=settings.get("data_dir", "PC_ENGINE/data/radar"),
            horizons_ms=tuple(settings.get("horizons_ms", (1000, 5000, 15000, 60000))),
        )
        self.lead_lag = LeadLagSignalEngine(settings.get("data_dir", "PC_ENGINE/data/radar"))
        self.regime = MarketRegimeEngine()
        self.min_lead_lag_confidence = float(settings.get("min_lead_lag_confidence", 0.75))

    @staticmethod
    def _returns(ohlcv: list[list[float]], limit: int = 20) -> list[float]:
        closes = [float(c[4]) for c in ohlcv if len(c) >= 5 and float(c[4]) > 0]
        closes = closes[-(limit + 1):]
        return [(closes[i] - closes[i - 1]) / closes[i - 1] for i in range(1, len(closes))]

    def evaluate_and_record(
        self,
        symbol: str,
        price: float,
        ohlcv: list[list[float]],
        technical_action: str,
        technical_strength: float,
        pattern_bias: float,
        radar_pressure: float = 0.0,
    ) -> ConfluenceRuntimeResult:
        learned = [
            signal for signal in self.lead_lag.signals(self.min_lead_lag_confidence)
            if signal.symbol == symbol
        ]
        regime = self.regime.classify(self._returns(ohlcv))
        score = self.engine.evaluate(
            symbol=symbol,
            technical_action=technical_action,  # type: ignore[arg-type]
            technical_strength=technical_strength,
            pattern_bias=pattern_bias,
            radar_pressure=radar_pressure,
            lead_lag_signals=learned,
            regime=regime,
        )
        self.tracker.record(symbol, price, score)
        return ConfluenceRuntimeResult(score=score, recorded=True)

    def summary(self) -> dict[str, Any]:
        return self.tracker.summary()
