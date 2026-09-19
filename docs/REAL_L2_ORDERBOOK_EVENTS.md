# Real L2 Order-Book Events

This layer adds normalized public Level-2 order-book events for Binance, OKX
and Coinbase Advanced Trade. It is observational/PAPER only.

OrderBookEvent carries venue/symbol, snapshot or delta type, exchange/provider
timestamp, monotonic and wall-clock receive timestamps, sequence when supplied,
and bid/ask price levels.

A delta is never treated as a complete book.

Venue adapters:
- Binance: depth@100ms, normalized as delta.
- OKX: books5, normalized as snapshot or delta from action.
- Coinbase Advanced Trade: level2, normalized as snapshot/update.

The next stage maintains venue-specific books, validates sequence continuity,
and feeds executable depth into PAPER microstructure replay.

No authentication, private account data, orders, withdrawals, CAPTCHA/2FA
bypass or exchange credentials are involved.
