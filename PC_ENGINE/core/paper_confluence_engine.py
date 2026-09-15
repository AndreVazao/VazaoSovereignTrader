from __future__ import annotations

from PC_ENGINE.core.confluence_runtime import PaperConfluenceRuntime
from PC_ENGINE.core.engine import SovereignEngine
from PC_ENGINE.core.strategy import Signal


class PaperConfluenceEngine(SovereignEngine):
    """SovereignEngine with the Confluence layer wired as a PAPER gate.

    The original strategy remains responsible for generating the technical
    proposal. Confluence can only downgrade BUY to HOLD. It cannot create a
    BUY, modify quantities, bypass Risk Engine checks, or execute orders.
    """

    def __init__(self, config: dict):
        super().__init__(config)
        settings = config.get("confluence", {})
        self.confluence_runtime = PaperConfluenceRuntime(settings)
        original_analyse = self.strategy.analyse

        def analyse_with_confluence(symbol: str, ohlcv: list[list[float]], spread_pct: float = 0.0) -> Signal:
            signal = original_analyse(symbol, ohlcv, spread_pct)
            if signal.action != "BUY" or not ohlcv:
                return signal
            price = float(ohlcv[-1][4]) if len(ohlcv[-1]) >= 5 else 0.0
            if price <= 0:
                return signal
            result = self.confluence_runtime.evaluate_and_record(
                symbol=symbol,
                price=price,
                ohlcv=ohlcv,
                technical_action=signal.action,
                technical_strength=signal.strength,
                pattern_bias=signal.pattern_bias,
                radar_pressure=0.0,
            )
            self.log("CONFLUENCE_PAPER", {
                "symbol": symbol,
                "action": result.score.action,
                "score": result.score.score,
                "confidence": result.score.confidence,
                "evidence": result.score.evidence,
                "contradictions": result.score.contradictions,
            })
            if result.score.action != "BUY":
                return Signal(
                    "HOLD",
                    signal.regime,
                    signal.strength,
                    "confluence gate: " + ("; ".join(result.score.contradictions) or "insufficient independent evidence"),
                    signal.stop_pct,
                    signal.take_profit_pct,
                    signal.pattern_bias,
                    signal.patterns,
                )
            return signal

        self.strategy.analyse = analyse_with_confluence  # type: ignore[method-assign]
