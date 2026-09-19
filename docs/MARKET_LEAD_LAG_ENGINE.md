# Market Lead/Lag Engine

The Trader is designed to study whether the same instrument or economically linked instruments are observed at different times across venues.

## Important distinction

A browser showing a price later than another venue does not prove that the underlying market moved later. The engine therefore measures:

- exchange/matching-engine event timestamp when available;
- provider/server timestamp;
- local receive timestamp;
- local processing timestamp;
- browser DOM observation timestamp;
- network RTT and clock offset estimate;
- sequence/update identifiers;
- bid/ask and trade events;
- order-book changes.

The system must distinguish a genuine venue lead/lag from display delay, network delay, batching, clock skew, browser rendering delay, stale pages, or different market definitions.

## Architecture

Data collectors should run simultaneously for each venue. API/WebSocket feeds are preferred for measurement; browser collectors are used where the platform exposes only a web interface. Browser automation is therefore a measurement/execution channel, not automatically the source of truth.

Each event is normalized into a common schema and stored with nanosecond/microsecond precision where the source provides it.

The analyzer should calculate rolling lead/lag distributions rather than a single delay number. It should report median, p95, p99, sample count, direction consistency, and persistence.

## Trading decision

A lead signal must never be interpreted as guaranteed future movement. Before live execution the engine should require configurable evidence thresholds, including minimum sample count, historical persistence, direction consistency, estimated execution latency, spread/slippage, fees, and risk limits.

The execution planner should identify:

1. observed leader;
2. candidate lagging venue;
3. measured event-time difference;
4. expected executable price;
5. estimated round-trip and order latency;
6. expected edge after costs;
7. confidence and freshness;
8. whether the signal remains valid immediately before execution.

## Current implementation direction

- API/WebSocket collectors for venues that expose real-time feeds.
- Browser collectors for web-only platforms.
- Clock/latency calibration.
- Cross-venue event correlation.
- Lead/lag detector.
- Historical evidence store.
- Replay/backtest engine.
- Paper execution before live execution.
- Live execution adapters only after the signal passes risk controls.

No CAPTCHA, 2FA bypass, anti-bot bypass, or platform security circumvention is part of this system.
