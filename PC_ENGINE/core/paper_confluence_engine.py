from __future__ import annotations

from PC_ENGINE.core.confluence_runtime import PaperConfluenceRuntime
from PC_ENGINE.core.engine import SovereignEngine
from PC_ENGINE.core.performance_gate import PerformanceGate
from PC_ENGINE.core.strategy import Signal


class PaperConfluenceEngine(SovereignEngine):
    """SovereignEngine with PAPER confluence and performance learning gates."""

    def __init__(self, config: dict):
        super().__init__(config)
        settings = config.get("confluence", {})
        self.confluence_runtime = PaperConfluenceRuntime(settings)
        self.performance_gate = PerformanceGate(
            data_dir=settings.get("data_dir", "PC_ENGINE/data/radar"),
            min_samples=int(settings.get("performance_min_samples", 100)),
            min_win_rate=float(settings.get("performance_min_win_rate", 0.52)),
            min_mean_net_bps=float(settings.get("performance_min_mean_net_bps", 0.0)),
            enforce=bool(settings.get("performance_enforce", True)),
        )
        self.performance_horizon_ms = int(settings.get("performance_horizon_ms", 15000))
        original_analyse = self.strategy.analyse

        def analyse_with_confluence(symbol: str, ohlcv: list[list[float]], spread_pct: float = 0.0) -> Signal:
            # Resolve older observations first, using the public websocket tape.
            self.confluence_runtime.tracker.resolve_from_websocket_events()
            signal = original_analyse(symbol, ohlcv, spread_pct)
            if not ohlcv or signal.regime == "WARMUP":
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
            if signal.action == "BUY" and result.score.action != "BUY":
                return Signal(
                    "HOLD", signal.regime, signal.strength,
                    "confluence gate: " + ("; ".join(result.score.contradictions) or "insufficient independent evidence"),
                    signal.stop_pct, signal.take_profit_pct, signal.pattern_bias, signal.patterns,
                )
            if signal.action == "BUY" and result.score.action == "BUY":
                gate = self.performance_gate.should_allow(symbol, "BUY", self.performance_horizon_ms)
                self.log("PERFORMANCE_GATE_PAPER", {
                    "symbol": symbol,
                    "status": gate.status,
                    "eligible": gate.eligible,
                    "samples": gate.samples,
                    "mean_net_bps": gate.mean_net_bps,
                    "win_rate": gate.win_rate,
                    "lower_ci_bps": gate.lower_ci_bps,
                    "reason": gate.reason,
                })
                if gate.status == "REJECTED" and self.performance_gate.enforce:
                    return Signal(
                        "HOLD", signal.regime, signal.strength,
                        "performance gate: " + gate.reason,
                        signal.stop_pct, signal.take_profit_pct, signal.pattern_bias, signal.patterns,
                    )
            return signal

        self.strategy.analyse = analyse_with_confluence  # type: ignore[method-assign]
