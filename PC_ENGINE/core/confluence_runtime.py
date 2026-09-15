from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from PC_ENGINE.core.confluence import ConfluenceEngine, ConfluenceScore
from PC_ENGINE.core.mean_reversion_strategy import MeanReversionStrategy
from PC_ENGINE.core.momentum_strategy import MultiTimeframeMomentumStrategy
from PC_ENGINE.core.paper_confluence_tracker import PaperConfluenceTracker
from PC_ENGINE.radar.lead_lag_signal import LeadLagSignalEngine
from PC_ENGINE.radar.regime_engine import MarketRegimeEngine

@dataclass(frozen=True)
class ConfluenceRuntimeResult:
    score: ConfluenceScore
    recorded: bool

class PaperConfluenceRuntime:
    """PAPER-only bridge for independent strategy evidence collection."""
    def __init__(self, settings: dict | None = None):
        settings = settings or {}
        self.engine = ConfluenceEngine(settings)
        self.tracker = PaperConfluenceTracker(
            data_dir=settings.get("data_dir", "PC_ENGINE/data/radar"),
            horizons_ms=tuple(settings.get("horizons_ms", (1000, 5000, 15000, 60000))),
        )
        self.lead_lag = LeadLagSignalEngine(settings.get("data_dir", "PC_ENGINE/data/radar"))
        self.regime = MarketRegimeEngine()
        self.momentum = MultiTimeframeMomentumStrategy(settings.get("momentum", {}))
        self.mean_reversion = MeanReversionStrategy(settings.get("mean_reversion", {}))
        self.min_lead_lag_confidence = float(settings.get("min_lead_lag_confidence", 0.75))

    @staticmethod
    def _returns(ohlcv: list[list[float]], limit: int = 20) -> list[float]:
        closes = [float(c[4]) for c in ohlcv if len(c) >= 5 and float(c[4]) > 0]
        closes = closes[-(limit + 1):]
        return [(closes[i] - closes[i - 1]) / closes[i - 1] for i in range(1, len(closes))]

    def evaluate_and_record(
        self, symbol: str, price: float, ohlcv: list[list[float]], technical_action: str,
        technical_strength: float, pattern_bias: float, radar_pressure: float = 0.0,
        timeframes: dict[str, list[list[float]]] | None = None,
    ) -> ConfluenceRuntimeResult:
        learned = [s for s in self.lead_lag.signals(self.min_lead_lag_confidence) if s.symbol == symbol]
        regime = self.regime.classify(self._returns(ohlcv))
        momentum = self.momentum.analyse(timeframes or {}).score if timeframes else 0.0
        mean_rev = self.mean_reversion.analyse(ohlcv, regime.name).score
        score = self.engine.evaluate(
            symbol=symbol, technical_action=technical_action, technical_strength=technical_strength,
            pattern_bias=pattern_bias, radar_pressure=radar_pressure, lead_lag_signals=learned,
            regime=regime, momentum_score=momentum, mean_reversion_score=mean_rev,
        )
        self.tracker.record(symbol, price, score)
        return ConfluenceRuntimeResult(score=score, recorded=True)

    def summary(self) -> dict[str, Any]:
        return self.tracker.summary()
