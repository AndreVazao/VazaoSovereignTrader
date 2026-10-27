# Real L2 Order-Book Events

This layer normalizes public Level-2 order-book events for Binance, OKX and
Coinbase Advanced Trade. It is observational/PAPER only.

OrderBookEvent carries venue/symbol, snapshot or delta type, exchange/provider
timestamp, monotonic and wall-clock receive timestamps, sequence when supplied,
and bid/ask price levels. A delta is never treated as a complete book.

Venue adapters:
- Binance: depth@100ms, normalized as delta.
- OKX: books5, normalized as snapshot or delta from action.
- Coinbase Advanced Trade: level2, normalized as snapshot/update.

The L2 collector wires each supported venue's synchronizer into a separate
synchronized-view JSONL output:
- binance_synchronized_orderbook_views.jsonl
- coinbase_synchronized_orderbook_views.jsonl
- okx_synchronized_orderbook_views.jsonl

The persistence contract fails closed for an unsupported venue; it does not
silently route unknown views into another venue's file. Regression tests cover
callback wiring, venue-specific paths, persistence routing and rejection of
unsupported venue names.

**Important remaining gate:** persisted synchronized views are telemetry, not
proof of an executable cross-venue edge. The normalized depth-edge adapter and
PAPER assessment must still be explicitly wired to a validated canonical
instrument mapping, current cost assumptions, freshness/skew checks and
evidence/replay. No live orders or execution authorization are provided here.

No authentication, private account data, orders, withdrawals, CAPTCHA/2FA
bypass or exchange credentials are involved.
