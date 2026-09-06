# Candlestick / Price Action Learning Layer

## Validation of the two reference images

The screenshots contain real and widely used technical-analysis concepts, but **the BUY/SELL labels are not all correct as universal rules**.

### Patterns that are valid concepts

- Dragonfly Doji — generally bullish/reversal context after a decline; confirmation is still required.
- Gravestone Doji — generally bearish/reversal context after a rise; confirmation is still required.
- Morning Star — bullish reversal setup after a decline.
- Bullish Engulfing — bullish reversal setup, especially after a decline.
- Three White Soldiers — bullish continuation/reversal pattern with three strong rising candles.
- Three Black Crows — bearish continuation/reversal pattern with three falling candles.
- Doji — indecision, not an automatic BUY or SELL.
- Hammer — usually a bullish reversal warning when it appears after a decline.
- Hanging Man — bearish warning when the same shape appears after an advance.

## Corrections applied to the source image

The second screenshot labels **Hammer as SELL** and **Hanging Man as BUY**. The engine does **not** copy those labels.

The distinction is contextual: the same candle shape can be interpreted differently depending on the preceding trend. Fidelity's technical-analysis material also treats Hammer/Hanging Man as context-dependent and notes that candlestick events are supplementary rather than standalone signals.

The engine therefore requires:

1. a valid candle geometry,
2. a relevant preceding trend where applicable,
3. trend/EMA/ATR/VWAP agreement,
4. spread and volatility filters,
5. risk-engine approval,
6. and only then an order decision.

## How this is used in VazaoSovereignTrader

`PC_ENGINE/core/candlestick_patterns.py` detects the patterns above and produces an evidence-weighted bias from -1 to +1.

`PC_ENGINE/core/strategy.py` uses that bias only as a **confirmation/refinement layer**. A candlestick pattern cannot create a BUY by itself. A strong bearish pattern can veto an otherwise bullish trend entry; a bullish pattern can increase confidence in an already valid bullish setup.

This is intentionally conservative for crypto, where 1-minute candles are noisy.

## Important limitation

These patterns are not proven to predict the future with certainty. Historical performance varies by asset, timeframe, market regime, liquidity and execution costs. The bot must learn their empirical expectancy from its own PAPER trades before giving them material weight in REAL mode.

The correct learning loop is:

`pattern -> context -> confirmation -> PAPER outcome -> expectancy -> weight adjustment`

not:

`pattern -> automatic BUY/SELL`.
