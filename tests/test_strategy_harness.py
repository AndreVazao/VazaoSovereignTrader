from __future__ import annotations

from dataclasses import dataclass

from PC_ENGINE.core.strategy_harness import PaperStrategyHarness, StrategyContext


@dataclass(frozen=True)
class Evidence:
    action: str
    score: float
    confidence: float
    reason: str
    extra: str = "kept"


def test_harness_normalizes_independent_strategy_outputs():
    harness = PaperStrategyHarness()
    harness.register("trend", lambda context: Evidence("BUY", 0.8, 0.9, "trend"))
    harness.register("reversion", lambda context: Evidence("SELL", 0.7, 0.6, "reversion"))

    context = StrategyContext(
        symbol="BTC/USDT",
        ohlcv=[],
        timeframes={},
        regime="RANGE",
    )
    result = harness.evaluate(context)

    assert result["trend"].score == 0.8
    assert result["trend"].action == "BUY"
    assert result["reversion"].score == -0.7
    assert result["reversion"].action == "SELL"
    assert result["trend"].metadata == {"extra": "kept"}
    assert all(item.paper_only for item in result.values())


def test_harness_fails_closed_when_strategy_raises():
    harness = PaperStrategyHarness()
    harness.register("broken", lambda context: (_ for _ in ()).throw(RuntimeError("boom")))

    result = harness.evaluate(
        StrategyContext(symbol="BTC/USDT", ohlcv=[], timeframes={})
    )

    assert result["broken"].action == "HOLD"
    assert result["broken"].score == 0.0
    assert result["broken"].confidence == 0.0
    assert result["broken"].reason.startswith("strategy failure:")
    assert result["broken"].metadata["error"] == "boom"


def test_harness_summary_is_observational_only():
    harness = PaperStrategyHarness()
    harness.register("a", lambda context: Evidence("BUY", 0.4, 0.5, "a"))
    harness.register("b", lambda context: Evidence("HOLD", 0.0, 0.0, "b"))
    harness.register("c", lambda context: Evidence("SELL", 0.2, 0.4, "c"))

    summary = harness.summary(
        StrategyContext(symbol="BTC/USDT", ohlcv=[], timeframes={})
    )

    assert summary["paper_only"] is True
    assert summary["counts"] == {"total": 3, "buy": 1, "sell": 1, "hold": 1}
