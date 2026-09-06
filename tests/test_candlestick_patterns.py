from __future__ import annotations

import unittest

from PC_ENGINE.core.candlestick_patterns import CandlestickPatternEngine


def candle(o: float, h: float, l: float, c: float) -> list[float]:
    return [0.0, o, h, l, c, 100.0]


class CandlestickPatternTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = CandlestickPatternEngine({"enabled": True, "min_confidence": 0.70})

    def test_bullish_engulfing(self) -> None:
        data = [
            candle(110, 112, 100, 102),
            candle(101, 115, 100, 114),
            candle(114, 116, 112, 115),
        ]
        names = [x.name for x in self.engine.detect(data)]
        self.assertIn("bullish_engulfing", names)

    def test_bearish_engulfing(self) -> None:
        data = [
            candle(100, 112, 99, 110),
            candle(111, 112, 98, 99),
            candle(99, 100, 95, 96),
        ]
        names = [x.name for x in self.engine.detect(data)]
        self.assertIn("bearish_engulfing", names)

    def test_dragonfly_doji_is_bullish_bias(self) -> None:
        data = [candle(100, 100.5, 90, 100), candle(99, 99.5, 89, 99), candle(100, 100.2, 90, 100.05)]
        bias, names, _ = self.engine.evaluate(data)
        self.assertIn("dragonfly_doji", names)
        self.assertGreater(bias, 0)

    def test_gravestone_doji_is_bearish_bias(self) -> None:
        data = [candle(90, 91, 89, 90.2), candle(95, 96, 94, 95.1), candle(100, 110, 99.8, 100.05)]
        bias, names, _ = self.engine.evaluate(data)
        self.assertIn("gravestone_doji", names)
        self.assertLess(bias, 0)

    def test_hammer_and_hanging_man_depend_on_context(self) -> None:
        downtrend = [candle(110, 111, 109, 109.5), candle(105, 106, 104, 104.5), candle(99, 100, 89, 100)]
        uptrend = [candle(90, 91, 89, 90.5), candle(95, 96, 94, 95.5), candle(99, 100, 89, 100)]
        down_names = [x.name for x in self.engine.detect(downtrend)]
        up_names = [x.name for x in self.engine.detect(uptrend)]
        self.assertIn("hammer", down_names)
        self.assertIn("hanging_man", up_names)


if __name__ == "__main__":
    unittest.main()
