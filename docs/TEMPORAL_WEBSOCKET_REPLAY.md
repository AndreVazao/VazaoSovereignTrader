# Temporal WebSocket Replay

Deterministic PAPER replay of normalized events collected by the public WebSocket layer.

## Flow

1. Load `PC_ENGINE/data/radar/websocket_events.jsonl`.
2. Restore `MarketEvent` objects.
3. Sort by exchange timestamp, provider timestamp, or local receive wall-clock fallback.
4. Feed the same event sequence into the real-time lead/lag detector.
5. When a signal appears, simulate execution after the configured latency.
6. Use only later events to measure the holding-period outcome.
7. Apply fees and slippage.
8. Compare lead/lag trades with a baseline that reacts to the follower's own qualifying moves.
9. Persist a machine-readable report.

## Safety

This module is PAPER-only. It never sends exchange orders and never requires private credentials.

The replay does not use future events to generate signals. Future events are used only after an entry decision to measure the outcome.

## Metrics

The report includes:

- events loaded/replayed
- lead/lag signals
- strategy trades and completed trades
- baseline trades and completed trades
- net PAPER P&L for both
- maximum drawdown
- opportunity capture rate
- missed opportunities caused by latency/data availability
- measured signal lag and latency-decay indicator

## Run

`python PC_ENGINE/tools/run_temporal_replay.py`

Optional:

`python PC_ENGINE/tools/run_temporal_replay.py --capital 100 --holding-ms 1000 --latency-ms 80`

Default output:

`PC_ENGINE/data/replay/temporal_replay.json`

## Limitations

This first replay is not an order-book simulator. It does not model queue position, depth, individual price levels, exchange-specific rejection rules, or exact round-trip acknowledgement timing. Those are deliberate next-stage improvements before any REAL-mode consideration.
