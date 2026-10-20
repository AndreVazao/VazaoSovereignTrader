# Temporal Venue Research — latency and cross-exchange price discovery

**Status:** research plan / no live execution  
**Created:** 2026-10-20  
**Owner goal:** make cross-exchange update-time differences a first-class research domain in VazaoSovereignTrader.

## Objective

Determine whether observable differences in the arrival and publication of market data across venues contain a stable, executable, net-positive opportunity after costs and risk. Do not equate a chart difference, candle timestamp, delayed UI, or stale feed with an exploitable trading edge.

## Reference-system findings (conceptual study only)

The Freqtrade upstream exchange layer demonstrates several useful general engineering concerns worth independently designing for:
- venue-specific capability/behavior configuration rather than assuming all exchanges behave identically;
- market-data normalization, trade de-duplication, OHLCV cleanup and explicit handling of partial candles;
- websocket subscriptions and per-symbol/per-feed last-refresh tracking to detect a stuck order book;
- timeouts, reconnect/reset handling, rate limits/retries and exchange-specific semantics;
- precision/amount/contract conversions and venue-specific order behavior.

Relevant upstream source for study (do not copy into Sovereign Trader under the current clean-room boundary):
- https://github.com/freqtrade/freqtrade/blob/develop/freqtrade/exchange/exchange.py
- https://github.com/freqtrade/freqtrade/blob/develop/freqtrade/exchange/exchange_ws.py
- https://github.com/freqtrade/freqtrade/blob/develop/freqtrade/exchange/exchange_utils.py

These are not all Freqtrade inventions; many are common exchange-integration requirements. Sovereign Trader should implement its own contracts, data models, tests and code. The user's AndreVazao/freqtrade root LICENSE currently does not provide a clear licence grant, so no source code is to be imported on that basis.

## Critical distinction: clocks and timestamps

For each observation, keep separate fields rather than one ambiguous timestamp:
- exchange_event_time: venue-provided event timestamp, if present;
- exchange_publish_time: only if the venue documents/provides it;
- local_receive_wall_time_utc: local wall-clock receive time;
- local_receive_monotonic_ns: monotonic clock for elapsed-time measurement;
- sequence/update_id/trade_id: venue sequence/identity where available;
- feed_type: trade, best bid/ask, order book, ticker, candle;
- venue, symbol, market_type, connection_id, raw_payload_hash;
- clock_sync_uncertainty_ms, feed_health, gap/reconnect flags.

Do not compare exchange timestamps from different venues as if their clocks were synchronized. Compare local receive times from one instrumented collector first, while recording clock offset/uncertainty. An exchange event timestamp can help characterize feed behavior but does not by itself prove when a quote became executable.

## Research stages

### Stage 1 — read-only collection and instrumentation
- Use public market data only; no API keys or order endpoints.
- Collect WebSocket trades and best bid/ask/order-book updates from a small set of venues for the same instrument and comparable market type.
- Record raw arrival times, sequence gaps, reconnects, data age, bid/ask, spread, depth and timestamps.
- Use a single collector/host initially to reduce clock-comparison confounders; record local monotonic time and clock-sync quality.
- Mark delayed, stale, duplicated, out-of-order and missing events explicitly. Do not silently repair them into apparent opportunities.

### Stage 2 — distinguish feed delay from market opportunity
Classify each apparent lead/lag:
1. Display/candle sampling artefact: visible on chart but not in trade/order-book events.
2. Transport/collector artefact: collector, DNS, network, queueing, reconnect, or subscription difference.
3. Timestamp artefact: clock skew, coarse timestamp resolution, different timestamp semantics.
4. Venue feed delay: venue-published data arrives later at the collector, but executable price may already have changed.
5. Potential executable lag: the lagging venue still exposes sufficient depth at the old executable quote after the leading event, long enough to act.
6. Unconfirmed: insufficient samples or uncertain ordering.

Only category 5 advances to execution simulation.

### Stage 3 — conservative replay and net-edge model
- Reconstruct decisions strictly in local receive-time order; prohibit look-ahead.
- Model time-to-decision, order submission latency, venue acknowledgement, partial fill, rejection, rate limiting and cancel/replace delays.
- Use bid/ask and order-book depth, not last-trade prices alone.
- Subtract taker/maker fees as applicable, spread crossing, slippage, funding/borrow costs where relevant, and conservative adverse-selection assumptions.
- Test multiple latency percentiles and stressed conditions; account for queue position where the venue's public data cannot reveal it.
- Include no-fill, partial-fill, stale-data, disconnection, and post-submit unknown-outcome scenarios.
- Compare against a no-signal baseline and a simple non-latency baseline. Report confidence intervals, sample size, net expectancy, drawdown and opportunity frequency.

### Stage 4 — PAPER shadow mode
- Observe opportunities and produce proposed intents only; do not submit exchange orders.
- Record predicted entry, observable executable quote, estimated costs, expected edge, actual subsequent market path and reason for rejection.
- Separate forecast correctness from fillability. No simulated fill unless the replay model's price/depth/time assumptions support it.
- Require stable results across time windows, venues and market regimes before considering any execution experiment.

### Stage 5 — guarded future decision
Any future execution experiment needs a separate explicit review, risk limits, human approval, venue-specific capability tests, idempotent intent identity, reconciliation and safe handling of unknown outcomes. This document authorizes no live order, capital transfer, withdrawal, or REAL-mode change.

## Metrics and rejection conditions

Measure:
- lead/lag distribution in milliseconds with confidence intervals;
- age of best bid/ask and order-book depth at decision time;
- event-order stability under clock uncertainty and reconnects;
- rate of apparent signals that disappear before hypothetical arrival;
- estimated net edge after conservative costs;
- fill probability and adverse selection assumptions;
- edge stability by venue pair, instrument, session and market regime.

Reject or mark inconclusive if:
- ordering uncertainty overlaps the claimed lead/lag;
- the signal only appears in candles/UI and not event-level data;
- stale/gapped feeds explain the apparent advantage;
- old quotes are not executable at sufficient size;
- net edge vanishes after realistic costs or latency;
- the result depends on look-ahead, optimistic fills, or a narrow cherry-picked interval.

## Initial deliverable

Build an independent, read-only temporal_market_lab in a lab/satellite repository or isolated package after repository structure and licence checks. First deliverable should be a synthetic event-replay test harness with controllable event delays, clock skew, duplicates, gaps, out-of-order messages, spread, depth and fees. Then add public-data collectors. Keep it isolated from the production execution engine until the evidence justifies a reviewed integration.

## Architectural requirements

- Reuse Sovereign Trader's central engine and safety gates; never create a second order engine.
- The temporal research service is initially read-only and produces evidence/proposals, not orders.
- Each observation and replay must be reproducible from versioned data and configuration.
- Office, cockpit and Android display the same backend evidence; clients do not connect directly to exchanges using private credentials.
- Public Vercel rendezvous is not a market-data or order relay. No public API port or paid service is required for the initial lab.
