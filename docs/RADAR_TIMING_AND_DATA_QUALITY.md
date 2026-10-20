# Radar Timing Semantics and Data Quality

This note documents the timing contract implemented by `PC_ENGINE/radar/market_radar.py`.

## Do not conflate these clocks

Each accepted REST ticker snapshot records:

- `exchange_ts_ms`: timestamp supplied by the venue, if any. Its meaning and clock alignment depend on that venue/API.
- `local_ts_ms`: local wall-clock time when the response was received.
- `request_duration_ms`: elapsed duration measured with a monotonic clock around the request.
- `latency_ms`: retained temporarily for compatibility, but set to `null`. A local-wall-clock minus exchange timestamp is not a trustworthy estimate of exchange or one-way network latency.

Request duration includes client/network/server processing and is not one-way network latency. A monotonic clock is used only for elapsed intervals; wall-clock timestamps are retained for cross-record chronology.

## Data quality policy

- Invalid/non-finite prices, bid/ask, volume, or malformed source timestamps are rejected.
- A duplicate or non-increasing exchange timestamp for the same venue/symbol is rejected instead of being treated as a new market event.
- Rejected observations increment `quality_rejections_total` in persisted cycle records.
- Observations are labelled for descriptive analysis only. A missing source timestamp does not get silently replaced by a fabricated exchange timestamp.
- The source timestamp is not assumed to share the PC's clock or a consistent semantic across venues.

## Lead/lag is still only a candidate

REST requests are made sequentially. Receive order can reflect polling order, network routing, server processing, and response buffering. Therefore each generated event has `evidence_status="polling_order_unconfirmed"`, and the JSONL record declares `lead_lag_semantics="candidate_only_polling_receive_order_unconfirmed"`.

These events are investigation candidates, not a trading signal and not proof of a leader/follower advantage. A future validation path needs exchange-native streams with documented timestamp semantics, clock-offset/uncertainty measurements, event-time replay, bid/ask/depth, execution costs, realistic latency/fill assumptions, and out-of-sample validation. The radar has no order path.

## Compatibility note

The existing `latency_ms` snapshot field remains present but is now `null` to avoid silently publishing a false latency value. Consumers should use `request_duration_ms` only to understand the local REST request duration, and must check `timing_quality` / `observation_status` before interpreting records.
