from __future__ import annotations

import unittest

from PC_ENGINE.core.candlestick_patterns import CandlestickPatternEngine


def candle(o: float, h: float, l: float, c: float) -> list[float]:
    return [0.0, o, h, l, c, 100.0]


class CandlestickPatternTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = CandlestickPatternEngine({"enabled": True, "min_confidence": 0.70})

    def test_bullish_engulfing(self) -> None:
        data = [candle(110, 112, 100, 102), candle(101, 115, 100, 114), candle(114, 116, 112, 115)]
        self.assertIn("bullish_engulfing", [x.name for x in self.engine.detect(data)])

    def test_bearish_engulfing(self) -> None:
        data = [candle(100, 112, 99, 110), candle(111, 112, 98, 99), candle(99, 100, 95, 96)]
        self.assertIn("bearish_engulfing", [x.name for x in self.engine.detect(data)])

    def test_doji_bias(self) -> None:
        bullish = [candle(100, 100.5, 90, 100), candle(99, 99.5, 89, 99), candle(100, 100.2, 90, 100.05)]
        bearish = [candle(90, 91, 89, 90.2), candle(95, 96, 94, 95.1), candle(100, 110, 99.8, 100.05)]
        bias, names, _ = self.engine.evaluate(bullish)
        self.assertIn("dragonfly_doji", names)
        self.assertGreater(bias, 0)
        bias, names, _ = self.engine.evaluate(bearish)
        self.assertIn("gravestone_doji", names)
        self.assertLess(bias, 0)

    def test_hammer_family_depends_on_context(self) -> None:
        downtrend = [candle(110, 111, 109, 109.5), candle(105, 106, 104, 104.5), candle(99, 100, 89, 100)]
        uptrend = [candle(90, 91, 89, 90.5), candle(95, 96, 94, 95.5), candle(99, 100, 89, 100)]
        self.assertIn("hammer", [x.name for x in self.engine.detect(downtrend)])
        self.assertIn("hanging_man", [x.name for x in self.engine.detect(uptrend)])

    def test_inverted_hammer_and_shooting_star_depend_on_context(self) -> None:
        downtrend = [candle(110, 111, 109, 109.5), candle(105, 106, 104, 104.5), candle(99, 110, 98, 102)]
        uptrend = [candle(90, 91, 89, 90.5), candle(95, 96, 94, 95.5), candle(99, 110, 98, 102)]
        self.assertIn("inverted_hammer", [x.name for x in self.engine.detect(downtrend)])
        self.assertIn("shooting_star", [x.name for x in self.engine.detect(uptrend)])

    def test_piercing_and_dark_cloud_cover(self) -> None:
        bullish = [candle(110, 112, 100, 102), candle(103, 108, 101, 107), candle(107, 109, 102, 105)]
        bearish = [candle(100, 110, 99, 108), candle(107, 109, 101, 102), candle(102, 104, 98, 100)]
        self.assertIn("piercing_line", [x.name for x in self.engine.detect(bullish)])
        self.assertIn("dark_cloud_cover", [x.name for x in self.engine.detect(bearish)])

    def test_harami_and_tweezers(self) -> None:
        bullish = [candle(110, 112, 100, 102), candle(103, 106, 100, 104), candle(104, 106, 101, 105)]
        bearish = [candle(100, 112, 99, 110), candle(109, 111, 106, 108), candle(108, 110, 105, 106)]
        self.assertIn("bullish_harami", [x.name for x in self.engine.detect(bullish)])
        self.assertIn("bearish_harami", [x.name for x in self.engine.detect(bearish)])
        tweezer_bottom = [candle(110, 112, 100, 102), candle(102, 108, 100, 106), candle(106, 109, 100, 108)]
        tweezer_top = [candle(100, 110, 95, 108), candle(108, 110, 101, 103), candle(103, 110, 100, 101)]
        self.assertIn("tweezer_bottom", [x.name for x in self.engine.detect(tweezer_bottom)])
        self.assertIn("tweezer_top", [x.name for x in self.engine.detect(tweezer_top)])

    def test_evening_star_and_three_inside_patterns(self) -> None:
        evening = [candle(100, 112, 99, 110), candle(110, 111, 108, 109.5), candle(109, 110, 100, 101)]
        inside_up = [candle(110, 112, 100, 102), candle(101, 107, 100, 106), candle(106, 114, 105, 113)]
        inside_down = [candle(100, 112, 99, 110), candle(109, 111, 105, 104), candle(104, 107, 96, 98)]
        self.assertIn("evening_star", [x.name for x in self.engine.detect(evening)])
        self.assertIn("three_inside_up", [x.name for x in self.engine.detect(inside_up)])
        self.assertIn("three_inside_down", [x.name for x in self.engine.detect(inside_down)])

    def test_rising_and_falling_three_methods(self) -> None:
        rising = [
            candle(100, 112, 99, 111), candle(110, 111, 105, 108), candle(108, 110, 104, 106),
            candle(106, 109, 103, 107), candle(107, 116, 106, 115),
        ]
        falling = [
            candle(111, 112, 99, 100), candle(101, 106, 100, 104), candle(104, 107, 101, 106),
            candle(106, 108, 102, 107), candle(107, 108, 95, 96),
        ]
        self.assertIn("rising_three_methods", [x.name for x in self.engine.detect(rising)])
        self.assertIn("falling_three_methods", [x.name for x in self.engine.detect(falling)])

    def test_spinning_top_and_marubozu(self) -> None:
        spinning = [candle(110, 112, 108, 109), candle(105, 107, 103, 105.5), candle(100, 105, 95, 102)]
        bullish = [candle(100, 110, 100, 109.5), candle(100, 110, 100, 109.5), candle(100, 110, 100, 109.5)]
        self.assertIn("spinning_top", [x.name for x in self.engine.detect(spinning)])
        self.assertIn("bullish_marubozu", [x.name for x in self.engine.detect(bullish)])


if __name__ == "__main__":
    unittest.main()
