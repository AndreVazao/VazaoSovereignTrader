from PC_ENGINE.core.candlestick_evidence import detect_candlestick_patterns, analyze_candlesticks


def candle(ts, o, h, l, c, v=10):
    return [ts, o, h, l, c, v]


def names(rows):
    return {item.name for item in detect_candlestick_patterns(rows)}


def test_evidence_uses_canonical_pattern_names():
    rows = [
        candle(1, 110, 112, 100, 102),
        candle(2, 103, 106, 100, 104),
        candle(3, 104, 106, 101, 105),
    ]
    found = names(rows)
    assert "bullish_harami" in found
    assert "three_inside_up_candidate" not in found


def test_evidence_covers_expanded_library():
    cases = [
        (
            [candle(1, 110, 112, 100, 102), candle(2, 103, 106, 100, 104), candle(3, 104, 106, 101, 105)],
            "bullish_harami",
        ),
        (
            [candle(1, 100, 110, 95, 108), candle(2, 108, 110, 101, 103), candle(3, 103, 110, 100, 101)],
            "tweezer_top",
        ),
        (
            [candle(1, 100, 110, 100, 109.5), candle(2, 100, 110, 100, 109.5), candle(3, 100, 110, 100, 109.5)],
            "bullish_marubozu",
        ),
        (
            [candle(1, 100, 112, 99, 110), candle(2, 110, 111, 108, 109.5), candle(3, 109, 110, 100, 101)],
            "evening_star",
        ),
    ]
    for rows, expected in cases:
        assert expected in names(rows)


def test_evidence_keeps_paper_only_contract():
    rows = [
        candle(1, 110, 112, 100, 102),
        candle(2, 101, 115, 100, 114),
        candle(3, 114, 116, 112, 115),
    ]
    evidence = analyze_candlesticks(rows)
    assert evidence.paper_only is True
    assert evidence.bias > 0
    assert evidence.dominant == "bullish_engulfing"


def test_malformed_rows_are_ignored_without_changing_valid_detection():
    rows = [
        [1, float("nan"), 1, 1, 1, 1],
        [2, 110, 112, 100, 102, 10],
        [3, 101, 115, 100, 114, 10],
        [4, 114, 116, 112, 115, 10],
    ]
    assert "bullish_engulfing" in names(rows)
