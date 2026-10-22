# Open-source trading architecture study — 2026-10-22

## Purpose and method

This is an architecture study, not a claim that any reference project is production-safe for our use case. Repositories and official documentation were inspected to identify design patterns that can be independently implemented in VazaoSovereignTrader. No source code was copied and no dependency was added as part of this study. Recheck licenses and upstream behavior before any future reuse.

## Reference projects

| Project | License (upstream declaration) | Useful patterns to study | Constraints for Sovereign Trader |
|---|---|---|---|
| [Freqtrade](https://github.com/freqtrade/freqtrade) | GPL-3.0 (verify current repository license before reuse) | Dry-run/PAPER separation, historical backtesting, exchange capability checks, persistence, health/operations and deterministic tests | Learn behavior and architecture; do not copy code or assume GPL compatibility |
| [Hummingbot](https://github.com/hummingbot/hummingbot) | Apache-2.0 | Modular exchange connectors, clear strategy/connector boundaries, broad exchange integration, separate API/dashboard/control plane | Evaluate connector lifecycle and error handling before considering dependencies; keep our engine authoritative and UI non-authoritative |
| [CCXT](https://github.com/ccxt/ccxt) | MIT | Capability discovery (has), unified market metadata, exchange-specific fallbacks and normalized APIs | Normalization does not remove exchange-specific semantics; never assume every venue supports identical methods or sequence contracts |
| [NautilusTrader](https://github.com/nautechsystems/nautilus_trader) | LGPL-3.0-only in current project metadata | Event-driven architecture, deterministic simulation, typed market events, separation of data/strategy/execution and broad automated testing | Strong architectural reference; not adopting its runtime or copying source without a separate dependency/license decision |
| [Official Binance Spot API docs](https://github.com/binance/binance-spot-api-docs/blob/master/web-socket-streams.md) | Documentation repository; check its terms if reusing content | Snapshot + buffered diff-depth replay, U/u sequence contract, explicit reconnect behavior | Venue-specific rules; cannot be generalized to OKX or Coinbase |
| [Coinbase Advanced Trade WebSocket docs](https://docs.cdp.coinbase.com/advanced-trade-apis/websocket/websocket-overview) | Official API documentation | level2 subscription and sequence-bearing l2_data envelope | Validate product identity and sequence; protocol parser alone is not a synchronized book |

## Patterns to apply to our own code

### 1. Preserve the native venue contract before normalizing

The existing PC_ENGINE/market_events/l2_collectors.py maps venue messages into OrderBookEvent. Keep exchange-specific parsing explicit and test it against captured, non-secret protocol fixtures. Normalize fields only after validating the venue-specific envelope, symbol/product, timestamp, sequence and event type. Never fabricate sequence IDs.

### 2. Make book validity fail-closed

The current Binance path contains binance_book_sync.py and binance_book_state.py: bounded buffering, REST snapshot, diff-depth replay, sequence-gap/overflow/disconnect invalidation and a freshness-gated view. Keep invalidation notifications visible to consumers so a last-good book cannot remain silently eligible. A snapshot or raw JSONL event stream is not proof of a synchronized order book.

### 3. Separate data, research, risk, execution and interface

Keep collectors observational. Research/edge calculation must consume only eligible, fresh, correctly identified books. Risk gates and PAPER execution remain separate. The cockpit/virtual office can display state and request actions but must not become the source of truth or block the headless engine. Existing department endpoints are read-only handlers, not evidence of independent autonomous agents.

### 4. Require comparable evidence before any temporal-edge claim

A candidate needs aligned instrument identity, synchronized books or explicitly comparable top-of-book data, source/receive timestamps, clock-health, bounded staleness, liquidity, fees, spread, slippage, funding where relevant, latency and inventory/fill assumptions. Evaluate chronological out-of-sample PAPER/shadow results; do not use future information, and do not infer profitability from a price difference alone.

### 5. Test failures, not just happy paths

For each exchange, add deterministic tests for snapshot bootstrap, duplicate/old messages, sequence gap, out-of-order update, malformed numeric levels, wrong product, stale view, disconnect, buffer overflow, failed snapshot, reconnect/recovery and callback/persistence errors. Test that every invalid state clears eligibility. Keep tests offline with injected snapshot fetchers; do not require exchange credentials in CI.

## Current implementation status

- Present in source: normalized market event timing; venue-specific L2 parsing for Binance/OKX/Coinbase; generic sequence-aware book builder; Binance Spot snapshot synchronizer and explicit ineligible states; health telemetry.
- Recently integrated: Coinbase Advanced Trade l2_data envelope parsing with sequence_num and product validation (PR #442).
- Not yet proven: production-grade synchronization for OKX and Coinbase; that all synchronized books are wired into the temporal-edge calculator; cross-exchange canonical instrument equivalence; net edge after costs; physical PC/APK behavior.
- Not authorized: REAL trading. Keep PAPER/read-only until separate risk, reconciliation, and user-device acceptance gates pass.

## Review cadence

For each new reference project, record: official source URL, license, inspected components, specific pattern, our independent implementation location, tests/evidence, unresolved differences and whether a dependency or source reuse is proposed. Do not add a dependency merely because a project is popular.
