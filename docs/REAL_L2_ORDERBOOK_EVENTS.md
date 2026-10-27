# Real L2 Order-Book Events

This layer normalizes public Level-2 order-book events for Binance, OKX and
Coinbase Advanced Trade. It is observational/PAPER only.

OrderBookEvent carries venue/symbol, snapshot or delta type, exchange/provider
timestamp, monotonic and wall-clock receive timestamps, sequence when supplied,
and bid/ask price levels. A delta is never treated as a complete book.

Venue adapters:
- Binance: depth@100ms, normalized as delta.
- OKX: books5 and bbo-tbt pushes are normalized as full snapshots; incremental
  books updates are normalized as deltas. Empty equal-sequence books heartbeats
  refresh liveness without claiming a delta sequence range.
- Coinbase Advanced Trade: level2 snapshots/updates are normalized as atomic
  events. A rejected or unsupported event clears the reconstructed book and
  requires a fresh snapshot before it can become eligible again.

The collector wires synchronized views into separate venue-specific JSONL files:
- `binance_synchronized_orderbook_views.jsonl`
- `coinbase_synchronized_orderbook_views.jsonl`
- `okx_synchronized_orderbook_views.jsonl`

Persistence is explicitly routed by venue. Unknown venue names fail closed rather
than being attributed to another exchange's output. Regression tests cover
routing, unsupported venue rejection, Coinbase invalidation, and OKX heartbeat
semantics.

**Important remaining gate:** synchronized views are telemetry, not proof of an
executable cross-venue edge. The depth-edge adapter and PAPER assessment still
require validated canonical instrument mapping, freshness/skew checks, current
fees/slippage assumptions, replay and out-of-sample evidence. No live orders or
execution authorization are provided here.

No authentication, private account data, orders, withdrawals, CAPTCHA/2FA
bypass or exchange credentials are involved.
