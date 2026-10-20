# Freqtrade Capability Study — Clean-Room Adaptation Plan

**Status:** research/design baseline; no Freqtrade source copied into Sovereign Trader  
**Date:** 2026-10-20  
**Scope:** learn from exchange integration, data quality, market replay, and operations; preserve Sovereign Trader's own engine and risk authority.

## Executive conclusion

Freqtrade is useful as a maturity reference because its exchange layer treats venue differences as an ongoing engineering concern rather than assuming that one generic API call behaves identically everywhere. Its README advertises a broad set of spot and futures venues, while the implementation uses a shared exchange base, venue-specific capability overrides, runtime capability checks, precision helpers, retries, and WebSocket lifecycle management.

Sovereign Trader already has useful foundations: a CCXT client, REST market radar, native WebSocket radar adapters for Binance/Coinbase/OKX public trades, a PAPER-oriented lead/lag path, replay/backtesting components, and an order-client identity/reconciliation boundary. The next step is not to replace the project with Freqtrade. It is to formalize the gaps between the current pieces and build our own exchange capability/data-quality contracts around the existing authoritative engine.

## Source and licensing boundary

Reference material examined:
- User's fork: https://github.com/AndreVazao/freqtrade
- Exchange base and behavior configuration: https://github.com/AndreVazao/freqtrade/blob/main/freqtrade/exchange/exchange.py
- Exchange capability helpers and retry policy: https://github.com/AndreVazao/freqtrade/blob/main/freqtrade/exchange/common.py
- WebSocket lifecycle: https://github.com/AndreVazao/freqtrade/blob/main/freqtrade/exchange/exchange_ws.py
- Exchange resolver: https://github.com/AndreVazao/freqtrade/blob/main/freqtrade/resolvers/exchange_resolver.py
- BingX-specific capability example: https://github.com/AndreVazao/freqtrade/blob/main/freqtrade/exchange/bingx.py
- Upstream project: https://github.com/freqtrade/freqtrade

The fork's root LICENSE currently says “Bot copiado para experiência.”, while its pyproject.toml declares GPLv3. That is a licensing ambiguity, not a clear permission to transplant files. Until ownership, upstream provenance, and obligations are resolved, use this study as conceptual reference only: no code, copied tests, or distinctive implementation text should be imported. If code reuse is later desired, review the upstream licence and compatibility obligations explicitly first. Personal use does not automatically remove licence obligations.

## What is worth learning

### 1. A common exchange contract plus explicit venue capabilities

The reference system has a common exchange class, a resolver, and per-venue overrides. Its capability metadata distinguishes supported methods and features, including WebSocket, order-book/ticker behavior, candle limits, stop orders, time-in-force, trade history, futures functions, and other venue-specific details. It can identify unsupported/missing capabilities instead of assuming all CCXT venues are interchangeable.

**Sovereign Trader adaptation:** introduce our own declarative capability registry and adapter contract. For every venue/market type, record:
- public market-data methods available (trades, ticker, best bid/ask, L2 book, candles);
- transport (REST/WebSocket), timestamp semantics and sequence/update identifiers;
- symbol naming/market type and instrument identity;
- precision, amount step, minimum quantity/notional, contract size where applicable;
- rate limits, retry classes, pagination/history limits and known unsupported operations;
- private/order capabilities only as a separate future execution concern;
- validation status, test date, library/API version, and source for every claim.

“Known by CCXT” must not mean “validated by Sovereign Trader.” A venue can be discoverable but only partially supported. Capability discovery should fail closed when a required feature is unknown.

### 2. Normalize market data without erasing source truth

The reference implementation has explicit data conversion and cleanup helpers, including trade de-duplication and OHLCV cleanup. That is a useful principle: normalization should make comparable records, but preserve the original venue identifiers and quality information.

**Sovereign Trader adaptation:** define an immutable normalized market event that retains:
- venue, market type, canonical instrument and venue symbol;
- event kind (trade, best bid/ask, book delta/snapshot, candle);
- source event timestamp and its documented meaning;
- local UTC receive wall time plus local monotonic receive time;
- source sequence/trade/update ID when available;
- bid/ask, quantities/depth, price, trade side, and raw payload hash/reference;
- feed health, age, sequence-gap/reconnect flags, and quality status.

Keep raw source evidence separate from derived features. Do not silently repair timestamp gaps, duplicate updates, invalid books, or missing bid/ask into a signal. Do not treat candle timestamps as proof of quote execution time.

### 3. WebSocket lifecycle is part of correctness

The reference WebSocket service tracks subscribed data, refresh/request times, manages its event loop and background tasks, and provides cleanup/reset behavior. Its exchange layer also uses retries/backoff and rate-limit handling.

**Sovereign Trader adaptation:** the native WebSocket radar currently has adapters for Binance, Coinbase, and OKX public trades; this is not broad exchange coverage. Add venues only behind a common lifecycle contract:
- explicit connect/subscription/ready states;
- heartbeat and last-event age;
- reconnect counters, exponential backoff with jitter, and bounded retry;
- resubscription after reconnect;
- sequence-gap detection and snapshot resynchronization where the protocol supports it;
- per-feed stale/degraded/healthy status;
- deterministic shutdown and no orphaned threads/tasks;
- public-data-only configuration for the research collector.

Do not label a feed healthy merely because its socket is connected. It must be producing timely, valid, expected events.

### 4. Venue behavior must be tested, not inferred

The BingX-specific reference is a small example of explicit overrides: candle limit, stop-loss support/order types, time-in-force values, and trade-history limitations differ from generic defaults.

**Sovereign Trader adaptation:** start with read-only venue conformance tests for Binance, BingX, OKX, Bybit, and Coinbase. Test symbols/market types, ticker fields, bid/ask sanity, order-book structure, timestamp behavior, rate-limit responses, reconnect behavior, and historical-data availability. Keep each result as dated evidence with API/library version. Add private endpoints only in a separately reviewed phase.

### 5. Backtesting and research tools need stronger guardrails

The reference project includes historical data download/conversion, backtesting, parameter optimization, and look-ahead/recursive analysis. Those are valuable categories of tooling, but their existence does not validate any particular strategy or prove profitability.

**Sovereign Trader adaptation:** prioritize correctness before optimization:
1. deterministic event replay with event-time and receive-time preserved;
2. no look-ahead checks and explicit train/validation/test time splits;
3. bid/ask and order-book-aware entry/exit simulation where data permits;
4. fees, spread, slippage, funding/borrow costs where relevant, latency, fill probability and adverse selection;
5. out-of-sample and regime-separated results, with uncertainty and sample counts;
6. PAPER shadow observations/intents with a hard boundary from live order submission.

Only after these controls are reliable should strategy search or machine-learning experiments be expanded. Parameter optimization on biased data only optimizes the bias.

## Current Sovereign Trader baseline found in source

- PC_ENGINE/exchanges/ccxt_client.py already wraps CCXT and provides OHLCV, ticker, spread, balances, order placement methods and order lookup/reconciliation methods. Its current generic wrapper does not by itself constitute a tested support matrix for every venue.
- PC_ENGINE/exchanges/base.py defines a shared client interface and fail-closed defaults for unsupported order reconciliation.
- PC_ENGINE/radar/market_radar.py is REST polling and has now been hardened so wall-clock minus exchange timestamp is not misreported as latency; REST lead/lag remains candidate-only.
- PC_ENGINE/radar/websocket_radar.py has native public-trade adapters for Binance, Coinbase and OKX, event counters, reconnect/error tracking and last-event-age telemetry. Its MarketEvent currently has millisecond wall-clock fields and a local_receive_latency_ms field; the next timing audit should verify how that field is computed and add monotonic nanoseconds/source semantics before it is used as evidence of an edge.
- PC_ENGINE/radar/fast_path_bridge.py connects market events to a deterministic router in PAPER mode. It has injectable risk/authorization/order callbacks; the mere presence of the bridge is not proof of live authorization or a validated trading edge.
- PC_ENGINE/radar/lead_lag_signal.py loads learned statistics and emits PAPER-only candidates.
- PC_ENGINE/backtest/replay.py validates OHLCV input and models fees/slippage, but the current simple candle loop is not an event-level, cross-venue latency replay and should not be used to certify temporal arbitrage.

## Priority plan

### Phase A — audit and contracts (next)
- Audit the WebSocket event timestamp/latency semantics and existing tests.
- Define the normalized event and exchange capability schemas.
- Add explicit capability and feed-health status to the cockpit/API without adding order authority.
- Keep main changes small; one implementation PR open at a time.

### Phase B — read-only adapters and conformance tests
- Add or refine public-data adapters one venue at a time, beginning with BingX because it is a stated target.
- Collect trades and best bid/ask; add L2 depth only when the adapter can prove snapshot/update consistency.
- Test rate limits, stale feeds, reconnects, symbol mapping, timestamp quality and sequence gaps with mocks and controlled public-data integration tests.

### Phase C — evidence and replay
- Persist raw observations with provenance and hashes, while keeping high-frequency data out of the learning-memory database.
- Build event-time replay and quality summaries.
- Compare polling, WebSocket receive order, and venue timestamps without conflating them.
- Run PAPER shadow evaluation with net-cost estimates and report rejected as well as accepted hypotheses.

### Phase D — private trading features (not authorized by this study)
- Only after public-data correctness and PAPER evidence are satisfactory, separately review order precision, minimum notional, order-state reconciliation, cancellation, partial fills, idempotency, secret handling and risk gates.
- No change to REAL-mode gates or live order behavior is included or authorized by this document.

## Acceptance criteria for calling an exchange “supported”

An exchange should not be called supported merely because CCXT can instantiate it. At minimum:
- documented spot/futures scope and symbol mapping;
- automated mocked tests for missing/malformed/stale data;
- a verified public market-data path with timestamps and health telemetry;
- retry/rate-limit/reconnect behavior covered by tests;
- current capability evidence with test date and dependency version;
- explicit list of unsupported methods/features;
- no order capability enabled by default from public-data conformance alone.

## Decision

Reuse the engineering lessons and the general ecosystem integration (CCXT) where its licence and dependency terms permit. Build Sovereign Trader's own contracts, validation, tests and learning workflow. The distinctive objective remains the evidence-driven, cross-exchange research system with one authoritative engine and risk boundary—not a copy of another bot.
