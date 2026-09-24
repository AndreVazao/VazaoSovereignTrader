from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from PC_ENGINE.core.breakout_strategy import BreakoutVolumeStrategy
from PC_ENGINE.core.confluence import ConfluenceEngine, ConfluenceScore
from PC_ENGINE.core.cost_model import OpportunityCostGate
from PC_ENGINE.core.mean_reversion_strategy import MeanReversionStrategy
from PC_ENGINE.core.momentum_strategy import MultiTimeframeMomentumStrategy
from PC_ENGINE.core.order_flow_strategy import OrderFlowStrategy
from PC_ENGINE.core.strategy_harness import PaperStrategyHarness, StrategyContext, StrategyEvidenceRecord
from PC_ENGINE.core.paper_confluence_tracker import PaperConfluenceTracker
from PC_ENGINE.radar.derivatives_radar import DerivativesRadar
from PC_ENGINE.radar.lead_lag_signal import LeadLagSignalEngine
from PC_ENGINE.radar.market_state import MarketStateStore, build_market_state
from PC_ENGINE.radar.regime_engine import MarketRegimeEngine
from PC_ENGINE.radar.trade_event_store import WebSocketTradeEventStore


@dataclass(frozen=True)
class ConfluenceRuntimeResult:
    score: ConfluenceScore
    recorded: bool


class PaperConfluenceRuntime:
    """PAPER-only bridge for independent strategy evidence and unified state collection."""

    def __init__(self, settings: dict | None = None):
        settings = settings or {}
        self.data_dir = settings.get("data_dir", "PC_ENGINE/data/radar")
        self.engine = ConfluenceEngine(settings)
        self.tracker = PaperConfluenceTracker(
            data_dir=self.data_dir,
            horizons_ms=tuple(settings.get("horizons_ms", (1000, 5000, 15000, 60000))),
        )
        self.state_store = MarketStateStore(self.data_dir)
        self.lead_lag = LeadLagSignalEngine(self.data_dir)
        self.regime = MarketRegimeEngine()
        self.momentum = MultiTimeframeMomentumStrategy(settings.get("momentum", {}))
        self.mean_reversion = MeanReversionStrategy(settings.get("mean_reversion", {}))
        self.order_flow = OrderFlowStrategy(settings.get("order_flow", {}))
        self.breakout = BreakoutVolumeStrategy(settings.get("breakout", {}))
        self.strategy_harness = PaperStrategyHarness()
        self.strategy_harness.register("momentum", lambda ctx: self.momentum.analyse(ctx.timeframes))
        self.strategy_harness.register("mean_reversion", lambda ctx: self.mean_reversion.analyse(ctx.ohlcv, ctx.regime))
        self.strategy_harness.register("order_flow", lambda ctx: self.order_flow.analyse(ctx.trade_events or []))
        self.strategy_harness.register("breakout", lambda ctx: self.breakout.analyse(ctx.ohlcv))
        derivatives_settings = settings.get("derivatives", {})
        self.derivatives = DerivativesRadar(
            exchanges=derivatives_settings.get("exchanges", ["binance", "bingx", "okx", "bybit"]),
            data_dir=self.data_dir,
            cache_seconds=float(derivatives_settings.get("cache_seconds", 10.0)),
        )
        self.derivatives_enabled = bool(derivatives_settings.get("enabled", True)) and bool(derivatives_settings.get("observational_only", True))
        self.trade_store = WebSocketTradeEventStore(
            self.data_dir,
            max_tail_bytes=int(settings.get("trade_event_tail_bytes", 2_000_000)),
        )
        self.trade_window_ms = max(250, int(settings.get("order_flow_window_ms", 5_000)))
        self.trade_max_events = max(1, int(settings.get("order_flow_max_events", 500)))
        self.min_lead_lag_confidence = float(settings.get("min_lead_lag_confidence", 0.75))
        self.cost_gate = OpportunityCostGate(
            minimum_net_edge_bps=float(settings.get("minimum_net_edge_bps", 2.0)),
            minimum_edge_margin_bps=float(settings.get("minimum_edge_margin_bps", 1.0)),
            max_total_cost_bps=float(settings.get("max_total_cost_bps", 100.0)),
        )

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
        timeframes: dict[str, list[list[float]]] | None = None,
        trade_events: list[dict] | None = None,
        record_state: bool = True,
        cost_context: dict | None = None,
    ) -> ConfluenceRuntimeResult:
        learned = [s for s in self.lead_lag.signals(self.min_lead_lag_confidence) if s.symbol == symbol]
        regime = self.regime.classify(self._returns(ohlcv))
        events = trade_events if trade_events is not None else self.trade_store.recent(symbol, self.trade_window_ms, self.trade_max_events)
        strategy_evidence = self.strategy_harness.evaluate(
            StrategyContext(
                symbol=symbol,
                ohlcv=ohlcv,
                timeframes=timeframes or {},
                regime=regime.name,
                trade_events=events,
            )
        )
        momentum = strategy_evidence["momentum"].score
        mean_rev = strategy_evidence["mean_reversion"].score
        order_flow = strategy_evidence["order_flow"].score
        breakout = strategy_evidence["breakout"].score
        trend_score = max(-1.0, min(1.0, float(technical_strength)))
        if str(technical_action).upper() == "SELL":
            trend_score = -trend_score
        elif str(technical_action).upper() == "HOLD":
            trend_score = 0.0
        strategy_evidence["trend_following"] = StrategyEvidenceRecord(
            strategy="trend_following",
            action=str(technical_action).upper() if str(technical_action).upper() in {"BUY", "SELL", "HOLD"} else "HOLD",
            score=round(trend_score, 6),
            confidence=round(max(0.0, min(1.0, float(technical_strength))), 6),
            reason="technical trend evidence supplied by engine",
            metadata={},
        )
        derivatives_score = 0.0
        if self.derivatives_enabled:
            derivatives_score = self.derivatives.evidence(symbol, price).score
        score = self.engine.evaluate(
            symbol=symbol,
            technical_action=technical_action,
            technical_strength=technical_strength,
            pattern_bias=pattern_bias,
            radar_pressure=radar_pressure,
            lead_lag_signals=learned,
            regime=regime,
            momentum_score=momentum,
            mean_reversion_score=mean_rev,
            order_flow_score=order_flow,
            breakout_score=breakout,
            derivatives_score=derivatives_score,
        )
        # Economic viability is evaluated after confluence evidence is assembled.
        # It never authorizes execution; it only blocks non-viable PAPER opportunities.
        if cost_context is not None and score.action in {"BUY", "SELL"}:
            breakdown = self.cost_gate.evaluate(
                gross_edge_bps=float(cost_context.get("gross_edge_bps", 0.0)),
                fee_bps=float(cost_context.get("fee_bps", 0.0)),
                spread_bps=float(cost_context.get("spread_bps", 0.0)),
                slippage_bps=float(cost_context.get("slippage_bps", 0.0)),
                liquidity_bps=float(cost_context.get("liquidity_bps", 0.0)),
                latency_bps=float(cost_context.get("latency_bps", 0.0)),
            )
            if not breakdown.viable:
                score = ConfluenceScore(
                    symbol=score.symbol,
                    action="HOLD",
                    score=0.0,
                    confidence=0.0,
                    evidence=score.evidence,
                    contradictions=score.contradictions + (f"opportunity gate: {breakdown.reason}",),
                    technical_score=score.technical_score,
                    candlestick_score=score.candlestick_score,
                    radar_score=score.radar_score,
                    lead_lag_score=score.lead_lag_score,
                    regime_score=score.regime_score,
                    momentum_score=score.momentum_score,
                    mean_reversion_score=score.mean_reversion_score,
                    order_flow_score=score.order_flow_score,
                    breakout_score=score.breakout_score,
                    derivatives_score=score.derivatives_score,
                    paper_only=True,
                )
        self.tracker.record(symbol, price, score, regime=regime.name)
        if record_state:
            state = build_market_state(
                symbol=symbol,
                price=price,
                regime=regime,
                technical_score=technical_strength if technical_action == "BUY" else -technical_strength if technical_action == "SELL" else 0.0,
                candlestick_bias=pattern_bias,
                radar_pressure=radar_pressure,
                lead_lag_score=sum(s.score for s in learned) / len(learned) if learned else 0.0,
                momentum_score=momentum,
                mean_reversion_score=mean_rev,
                order_flow_score=order_flow,
                breakout_score=breakout,
                derivatives_score=derivatives_score,
                confluence=score,
                strategy_evidence={name: evidence.__dict__ for name, evidence in strategy_evidence.items()},
            )
            self.state_store.append(state)
        return ConfluenceRuntimeResult(score=score, recorded=record_state)

    def resolve_outcomes(self, fee_bps_round_trip: float = 28.0) -> int:
        return self.tracker.resolve_from_websocket_events(fee_bps_round_trip)

    def summary(self) -> dict[str, Any]:
        return self.tracker.summary()

    def latest_state(self, symbol: str) -> dict | None:
        return self.state_store.snapshot(symbol)
