# High-Resolution Market Events

## Purpose

The GOD Ultra evolution starts by replacing ambiguous snapshot timing with a normalized event model. Every collector must preserve the timing chain instead of assuming that the timestamp visible in a browser represents when the market actually changed.

## Timing hierarchy

1. `exchange_ts_ms` — venue-reported event time when available.
2. `provider_ts_ms` — upstream/provider timestamp when supplied.
3. `local_receive_ns` — monotonic timestamp captured as close as possible to receipt.
4. `local_process_ns` — monotonic timestamp after normalization.
5. `browser_render_ns` — optional UI/render timing; never authoritative for market lead/lag.

The system must retain all available timestamps so latency can be measured rather than guessed.

## Event identity

Each normalized event receives a unique `event_id`. Venue sequence numbers are retained when available. Collectors must not synthesize exchange sequence numbers.

## Initial event types

- `trade`
- `ticker`
- `order_book_delta`
- `order_book_snapshot`
- `funding`
- `status`

More event types can be added without changing the timing contract.

## Next phase

This model is intentionally collector-agnostic. The next branch should add WebSocket collectors for the configured crypto venues and map their native messages into `MarketEvent`. REST polling remains a fallback/validation channel, not the preferred high-resolution timing source.

## Safety boundary

This layer is observational. It does not choose trades, allocate capital, or place orders. Lead/lag claims must still pass validation, cost, freshness, liquidity, clock-health, and risk gates before any execution path can consume them.
