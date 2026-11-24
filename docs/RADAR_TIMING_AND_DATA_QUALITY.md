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


## WebSocket source timestamp policy

The native Binance, Coinbase, and OKX public-trade parsers reject an event when its venue-provided trade timestamp is missing, malformed, or non-positive. They do not replace it with the collector's receive time. Collector receive time remains a separate field. This preserves the distinction between venue event-time evidence and local arrival-time evidence; a rejected event is preferable to a fabricated cross-venue lag.

## Public top-of-book ingestion gate

The WebSocket top-of-book collector applies a separate quality gate before writing ticker rows:

- Rejects non-finite/non-positive quotes, crossed or locked quotes, invalid local receive clocks, and observations whose monotonic receive age exceeds 30 seconds.
- Orders provider timestamps only within the same venue and normalized symbol. Older timestamps and exact duplicate observations are flagged as ineligible for analysis, but remain in the bounded raw JSONL evidence store.
- Equal provider timestamps with different quotes are retained but explicitly marked `SAME_TIMESTAMP_DIFFERENT_QUOTE`; they are not treated as a reliable event-time ordering.
- When a venue message has no provider timestamp (currently possible on the Coinbase ticker parser), the observation may be retained with `timestamp_quality="LOCAL_RECEIVE_ONLY"`. The collector never fabricates a provider timestamp from local time.
- The health snapshot exposes accepted, missing-timestamp, duplicate, out-of-order, invalid-observation, and bounded-tracker eviction counters. These counters describe data quality, not venue clock accuracy.
- Every parsed ticker observation is retained in the bounded raw evidence store, including flagged anomalies. Each row carries `analysis_eligible`, `quality_status`, and `quality_reason`; downstream research must exclude rows where `analysis_eligible` is false. Non-finite numeric fields are serialized as `null` rather than invalid JSON. Provider timestamp tracking is bounded to 4,096 venue/instrument keys.

Provider timestamps are deliberately not compared with local wall-clock time: without measured clock offset and uncertainty, that comparison could falsely reject valid events or label stale events as fresh. Cross-venue lead/lag remains unconfirmed.
