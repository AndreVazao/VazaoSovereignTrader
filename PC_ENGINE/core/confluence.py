from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from PC_ENGINE.radar.lead_lag_signal import PaperLeadLagSignal
from PC_ENGINE.radar.regime_engine import MarketRegime

Action = Literal["BUY", "SELL", "HOLD"]

@dataclass(frozen=True)
class ConfluenceScore:
    symbol: str
    action: Action
    score: float
    confidence: float
    evidence: tuple[str, ...]
    contradictions: tuple[str, ...]
    technical_score: float
    candlestick_score: float
    radar_score: float
    lead_lag_score: float
    regime_score: float
    momentum_score: float = 0.0
    mean_reversion_score: float = 0.0
    order_flow_score: float = 0.0
    breakout_score: float = 0.0
    paper_only: bool = True

class ConfluenceEngine:
    """Combines independent evidence without authorizing orders."""
    DEFAULT_WEIGHTS = {
        "technical": 0.25,
        "candlestick": 0.10,
        "radar": 0.10,
        "lead_lag": 0.14,
        "regime": 0.08,
        "momentum": 0.10,
        "mean_reversion": 0.06,
        "order_flow": 0.10,
        "breakout": 0.07,
    }

    def __init__(self, settings: dict | None = None):
        settings = settings or {}
        configured = settings.get("weights", {})
        self.weights = dict(self.DEFAULT_WEIGHTS)
        for key in self.weights:
            if key in configured:
                self.weights[key] = max(0.0, float(configured[key]))
        total = sum(self.weights.values()) or 1.0
        self.weights = {key: value / total for key, value in self.weights.items()}
        self.action_threshold = abs(float(settings.get("action_threshold", 0.35)))
        self.minimum_independent_evidence = max(1, int(settings.get("minimum_independent_evidence", 2)))
        self.contradiction_penalty = min(1.0, max(0.0, float(settings.get("contradiction_penalty", 0.25))))

    @staticmethod
    def _clamp(value: float) -> float:
        return max(-1.0, min(1.0, float(value)))

    @staticmethod
    def _direction(value: float, threshold: float = 0.10) -> int:
        if value > threshold:
            return 1
        if value < -threshold:
            return -1
        return 0

    def evaluate(
        self,
        symbol: str,
        technical_action: Action,
        technical_strength: float,
        pattern_bias: float = 0.0,
        radar_pressure: float = 0.0,
        lead_lag_signals: list[PaperLeadLagSignal] | None = None,
        regime: MarketRegime | None = None,
        momentum_score: float = 0.0,
        mean_reversion_score: float = 0.0,
        order_flow_score: float = 0.0,
        breakout_score: float = 0.0,
    ) -> ConfluenceScore:
        technical_score = self._clamp(technical_strength if technical_action == "BUY" else -technical_strength if technical_action == "SELL" else 0.0)
        candlestick_score = self._clamp(pattern_bias)
        radar_score = self._clamp(radar_pressure)
        momentum_score = self._clamp(momentum_score)
        mean_reversion_score = self._clamp(mean_reversion_score)
        order_flow_score = self._clamp(order_flow_score)
        breakout_score = self._clamp(breakout_score)
        lead_lag_score = 0.0
        if lead_lag_signals:
            values: list[float] = []
            for signal in lead_lag_signals:
                if signal.symbol != symbol or signal.expectancy_bps <= 0:
                    continue
                direction = 1.0 if signal.direction.upper() == "UP" else -1.0 if signal.direction.upper() == "DOWN" else 0.0
                values.append(direction * min(1.0, max(0.0, signal.confidence)))
            if values:
                lead_lag_score = self._clamp(sum(values) / len(values))
        regime_score = 0.0
        if regime is not None:
            if regime.trend == "UP":
                regime_score = min(1.0, regime.confidence)
            elif regime.trend == "DOWN":
                regime_score = -min(1.0, regime.confidence)
        components = {
            "technical": technical_score,
            "candlestick": candlestick_score,
            "radar": radar_score,
            "lead_lag": lead_lag_score,
            "regime": regime_score,
            "momentum": momentum_score,
            "mean_reversion": mean_reversion_score,
            "order_flow": order_flow_score,
            "breakout": breakout_score,
        }
        weighted = sum(self.weights[key] * value for key, value in components.items())
        directions = {key: self._direction(value) for key, value in components.items()}
        positive = sum(1 for value in directions.values() if value > 0)
        negative = sum(1 for value in directions.values() if value < 0)
        contradictions: list[str] = []
        if positive and negative:
            contradiction_count = min(positive, negative)
            weighted *= max(0.0, 1.0 - self.contradiction_penalty * contradiction_count)
            contradictions.append(f"evidências conflitantes: {positive} bullish vs {negative} bearish")
        evidence = []
        for key, value in components.items():
            if abs(value) >= 0.10:
                evidence.append(f"{key}={'bullish' if value > 0 else 'bearish'}:{value:.2f}")
        aligned_count = max(positive, negative)
        if aligned_count < self.minimum_independent_evidence:
            action: Action = "HOLD"
        elif weighted >= self.action_threshold:
            action = "BUY"
        elif weighted <= -self.action_threshold:
            action = "SELL"
        else:
            action = "HOLD"
        evidence_confidence = min(1.0, aligned_count / len(components)) if components else 0.0
        confidence = round((evidence_confidence * 0.55) + (min(1.0, abs(weighted)) * 0.45), 4)
        return ConfluenceScore(
            symbol=symbol, action=action, score=round(self._clamp(weighted), 4), confidence=confidence,
            evidence=tuple(evidence), contradictions=tuple(contradictions),
            technical_score=round(technical_score, 4), candlestick_score=round(candlestick_score, 4),
            radar_score=round(radar_score, 4), lead_lag_score=round(lead_lag_score, 4),
            regime_score=round(regime_score, 4), momentum_score=round(momentum_score, 4),
            mean_reversion_score=round(mean_reversion_score, 4), order_flow_score=round(order_flow_score, 4),
            breakout_score=round(breakout_score, 4), paper_only=True,
        )
