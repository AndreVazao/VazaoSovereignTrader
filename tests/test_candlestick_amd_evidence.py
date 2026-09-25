from PC_ENGINE.core.amd_phase import analyze_amd
from PC_ENGINE.core.candlestick_evidence import analyze_candlesticks, detect_candlestick_patterns
from PC_ENGINE.core.confluence_runtime import PaperConfluenceRuntime


def candle(ts, o, h, l, c, v=10):
    return [ts, o, h, l, c, v]


def test_bullish_engulfing_is_detected():
    rows = [
        candle(1, 105, 106, 97, 98),
        candle(2, 97, 104, 96, 103),
    ]
    patterns = detect_candlestick_patterns(rows)
    names = {item.name for item in patterns}
    assert "bullish_engulfing" in names
    evidence = analyze_candlesticks(rows)
    assert evidence.bias > 0


def test_hammer_is_detected_after_downtrend():
    rows = [
        candle(1, 105, 106, 103, 104),
        candle(2, 104, 105, 101, 102),
        candle(3, 102, 103, 98, 99),
        candle(4, 100, 102.5, 94, 102),
    ]
    names = {item.name for item in detect_candlestick_patterns(rows)}
    assert "hammer" in names


def test_morning_star_is_detected():
    rows = [
        candle(1, 110, 111, 100, 101),
        candle(2, 101, 103, 100, 102),
        candle(3, 102, 111, 101, 109),
    ]
    names = {item.name for item in detect_candlestick_patterns(rows)}
    assert "morning_star" in names


def test_amd_detects_low_sweep_and_bullish_displacement():
    rows = []
    for i in range(20):
        rows.append(candle(i, 100, 102, 98, 100.5))
    rows.append(candle(21, 100, 101, 97, 100.5))
    evidence = analyze_amd(rows, lookback=20)
    assert evidence.sweep == "LOW"
    assert evidence.phase == "MANIPULATION"
    assert evidence.direction == "BUY"
    assert evidence.score > 0


def test_runtime_records_candlestick_and_amd_evidence(tmp_path):
    rows = [
        candle(1, 105, 106, 103, 104),
        candle(2, 104, 105, 101, 102),
        candle(3, 102, 103, 98, 99),
        candle(4, 100, 102.5, 94, 102),
        candle(5, 102, 103, 100, 102),
        candle(6, 102, 104, 100, 103),
        candle(7, 103, 105, 101, 104),
        candle(8, 104, 106, 102, 105),
        candle(9, 105, 107, 103, 106),
        candle(10, 106, 108, 104, 107),
        candle(11, 107, 109, 105, 108),
        candle(12, 108, 110, 106, 109),
        candle(13, 109, 111, 107, 110),
        candle(14, 110, 112, 108, 111),
        candle(15, 111, 113, 109, 112),
        candle(16, 112, 114, 110, 113),
        candle(17, 113, 115, 111, 114),
        candle(18, 114, 116, 112, 115),
        candle(19, 115, 117, 113, 116),
        candle(20, 116, 118, 114, 117),
        candle(21, 117, 119, 115, 118),
        candle(22, 118, 120, 116, 119),
        candle(23, 119, 121, 117, 120),
        candle(24, 120, 122, 118, 121),
        candle(25, 121, 123, 119, 122),
    ]
    runtime = PaperConfluenceRuntime({
        "data_dir": str(tmp_path),
        "derivatives": {"enabled": False},
    })
    result = runtime.evaluate_and_record(
        symbol="BTC/USDT",
        price=122,
        ohlcv=rows,
        technical_action="HOLD",
        technical_strength=0.0,
        pattern_bias=0.0,
        radar_pressure=0.0,
        timeframes={"1m": rows},
        trade_events=[],
        record_state=False,
    )
    assert "candlestick" in runtime.strategy_harness.evaluate(
        __import__("PC_ENGINE.core.strategy_harness", fromlist=["StrategyContext"]).StrategyContext(
            symbol="BTC/USDT", ohlcv=rows, timeframes={"1m": rows}, trade_events=[]
        )
    )
    assert "amd_phase" in runtime.strategy_harness.evaluate(
        __import__("PC_ENGINE.core.strategy_harness", fromlist=["StrategyContext"]).StrategyContext(
            symbol="BTC/USDT", ohlcv=rows, timeframes={"1m": rows}, trade_events=[]
        )
    )
    assert result.score.paper_only is True
