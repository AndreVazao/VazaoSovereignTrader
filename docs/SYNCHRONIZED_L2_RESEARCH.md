# Synchronized L2 depth research

The public L2 collector persists synchronized, quality-labelled views to:

- `PC_ENGINE/data/radar/binance_synchronized_orderbook_views.jsonl`
- `PC_ENGINE/data/radar/coinbase_synchronized_orderbook_views.jsonl`
- `PC_ENGINE/data/radar/okx_synchronized_orderbook_views.jsonl`

Run the bounded PAPER research consumer after collection has produced data:

```powershell
python PC_ENGINE/replay/synchronized_l2_research.py --data-dir PC_ENGINE/data/radar --quote-notional 100 --fee-bps 10
```

The report is written to `PC_ENGINE/data/replay/synchronized_l2_research.json`. The default fee is zero; supply a conservative per-side fee assumption explicitly for cost estimates. The consumer does not fetch or verify venue fee schedules.

## Admission gates

Every row is independently checked for:

- `analysis_eligible=true`, `quality_status=VALID`, and PAPER-only provenance flags;
- synchronized status, valid non-negative sequence, positive observation timestamp and captured age within the configured maximum;
- finite positive price and quantity at every level, unique prices, correct side ordering, non-crossed best prices and bounded depth;
- strictly increasing sequence per venue/symbol within each synchronized epoch; an explicit invalid-book record resets the baseline for a later rebootstrap.

Flagged, malformed, stale, non-PAPER, duplicate or out-of-order records are excluded and counted. Raw collector evidence remains unchanged.

## Metrics

For a configurable quote notional, the consumer walks the asks for a simulated buy and bids for a simulated sell, recording fill quantity, VWAP, levels consumed, full/partial fill, impact versus mid, spread, depth imbalance and estimated impact-plus-assumed-fee cost.

The report is descriptive execution-cost research. It does not create signals, compare venues, infer canonical instrument equivalence, authorize execution, or submit orders. Cross-venue analysis remains blocked until market identity, quote/settlement units, timestamps, fees and operational assumptions are independently verified.

## Resource bounds and interpretation

Input is processed incrementally. At most 100,000 sample rows are retained by default; aggregate counters cover all accepted records. Each book is capped at 5,000 levels per side, each JSONL line at 4 MiB, and aggregate market groups at 1,024. The age field is the synchronizer's captured age at persistence time; monotonic timestamps are retained as provenance and are not compared across process clock domains.

This is a deterministic offline research command, not yet a scheduled service. Physical Windows testing and endurance testing on the target low-memory PC remain mandatory before unattended operation.
