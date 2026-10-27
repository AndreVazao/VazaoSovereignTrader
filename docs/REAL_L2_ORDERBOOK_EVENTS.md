# Real L2 Order-Book Events

This layer normalizes public Level-2 order-book events for Binance, OKX and
Coinbase Advanced Trade. It is observational/PAPER only.

OrderBookEvent carries venue/symbol, snapshot or delta type, exchange/provider
timestamp, monotonic and wall-clock receive timestamps, sequence when supplied,
and bid/ask price levels. A delta is never treated as a complete book.

Venue adapters:
- Binance: depth@100ms, normalized as delta.
- OKX: books5 and bbo-tbt pushes are full snapshots; incremental books updates
  are deltas. Empty equal-sequence books heartbeats refresh liveness without
  claiming a delta sequence range.
- Coinbase Advanced Trade: level2 snapshots/updates are atomic events. A
  rejected or unsupported event clears the reconstructed book and requires a
  fresh snapshot before the book can become eligible again.

The collector writes synchronized views to separate venue-specific JSONL files:
- `binance_synchronized_orderbook_views.jsonl`
- `coinbase_synchronized_orderbook_views.jsonl`
- `okx_synchronized_orderbook_views.jsonl`

Synchronized payloads retain explicit venue and symbol identity. Output paths
reject unsupported venue names instead of silently routing unknown views into
another exchange's file. Regression tests cover identity, routing boundaries,
Coinbase invalidation and OKX heartbeat semantics.

**Important remaining gate:** synchronized views are telemetry, not proof of an
executable cross-venue edge. A PAPER depth-edge assessment still requires
validated canonical instrument mapping, freshness/skew checks, current fees and
slippage assumptions, replay and out-of-sample evidence. No live orders or
execution authorization are provided here.

No authentication, private account data, orders, withdrawals, CAPTCHA/2FA
bypass or exchange credentials are involved.
