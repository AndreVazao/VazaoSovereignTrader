# WebSocket Market Collectors

This phase connects public real-time venue streams to the normalized MarketEvent contract.

## Initial venues

- Binance public market stream
- OKX public market stream
- Coinbase Advanced Trade public market stream

The first implementation supports public ticker/trade data only. Credentials are not required and no private/user channels are enabled.

## Timing

The collector captures local_receive_ns immediately when the WebSocket message reaches the client. Venue/provider timestamps are retained when present. Browser rendering is not involved in the timing path.

This allows the next latency-calibration phase to compare venue timestamps, local receipt timing, and processing delay without claiming that one platform's browser is earlier than another's market engine.

## Safety

Collectors are observational. They do not submit, cancel, modify, or sign orders.

## Operational note

Public WebSocket schemas change. Parsers must be tested against current venue documentation before promoting a collector to production-critical use. Unsupported messages are ignored rather than converted into fabricated events.

## Reconnection policy

The top-of-book service uses bounded exponential retry delays after a WebSocket disconnect: 1, 2, 4, 8, 16, then at most 30 seconds. A connection that remained open for at least 60 seconds is treated as stable and resets the next retry to 1 second. Short-lived connections do not reset the backoff. Connection duration is measured with a monotonic clock and exposed in the collector health snapshot. This policy affects public-data collection only; it does not authorize execution or alter PAPER mode.
