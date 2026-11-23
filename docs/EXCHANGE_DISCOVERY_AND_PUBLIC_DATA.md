# Exchange discovery and public-data bootstrap

## Purpose

VST's venue catalogue is extensible. Binance, Coinbase, OKX, BingX, Bybit and Bitget are initial public-research entries, not a permanent exchange allowlist. The registry separates catalogue presence from verified API support, account connection, jurisdiction eligibility and financial authority.

## Inspect the catalogue

From the repository root:

```powershell
python PC_ENGINE/tools/run_exchange_discovery.py
```

To also list exchange IDs shipped by the installed CCXT package that are not yet in the curated catalogue:

```powershell
python PC_ENGINE/tools/run_exchange_discovery.py --include-ccxt-leads
```

CCXT leads are only discovery hints. They are not automatically trusted, probed, enabled or recommended. Before adding one as a usable public venue, verify its legal identity, official domain and API documentation, product/symbol semantics, jurisdiction status, rate limits, public endpoint behavior and operational/security risks.

## Add a candidate

Create `PC_ENGINE/config/exchange_candidates.json` as a JSON array. Example:

```json
[
  {
    "venue_id": "examplevenue",
    "display_name": "Example Venue",
    "official_url": "https://official.example",
    "api_docs_url": "https://official.example/docs",
    "ccxt_id": "examplevenue"
  }
]
```

Use only provider-controlled HTTPS domains after verifying them independently. Candidate records are loaded as `discovered_unverified`, with public REST disabled and private account access unconfigured. Adding a candidate does not enable collection. A candidate must be reviewed and promoted through a code-reviewed catalogue change before the default radar will query it. Never add API keys, passwords, account IDs or private URLs to this file.

## Start public market-data collection

The default radar venue set is now derived from the reviewed public catalogue:

```powershell
python PC_ENGINE/tools/run_market_radar.py --cycles 20
```

Continuous public-only observation:

```powershell
python PC_ENGINE/tools/run_market_radar.py
```

A smaller diagnostic run:

```powershell
python PC_ENGINE/tools/run_market_radar.py --exchanges binance,okx --symbols BTC/USDT --interval 5 --cycles 12
```

Observations are written to the configured local data directory (default `PC_ENGINE/data/radar`). Keep this data directory private and outside Git. Public ticker polling is useful for initial coverage and descriptive research; it does not prove executable arbitrage or one-way network latency. Use synchronized native streams, validated order books, depth, fees, slippage and out-of-sample replay before treating an edge as meaningful.


## Continuous streams and bounded local storage

The native public WebSocket collectors derive their default venue set from the reviewed catalogue and the collector's implemented protocol mappings. At present, the reviewed stream path is Binance, OKX and Coinbase. BingX, Bybit and Bitget remain available to the REST/public research path only until their native stream adapters are separately implemented and validated. Unverified candidates cannot be selected for native streams.

Start top-of-book streams:

```powershell
python PC_ENGINE/tools/run_top_of_book_collector.py --symbols BTC/USDT ETH/USDT
```

Start synchronized L2 collection:

```powershell
python PC_ENGINE/tools/run_l2_market_data_collector.py --symbols BTC/USDT ETH/USDT
```

Both commands default to the reviewed native stream venues. To request a subset, pass `--venues binance okx`. A venue without a reviewed stream mapping is rejected instead of being silently treated as supported.

All three public collectors now use bounded JSONL persistence. The default cap is 64 MiB per active file and one 64 MiB rotated backup; the cap can be changed with `--max-file-mb` (maximum 512 MiB per file). This bounds each stream's active+backup data footprint but is not a permanent archive: older records are discarded when the backup is replaced. Export/copy data before it rotates if it must be retained for long-term research. Health files expose collector state and write/error counters.

The REST radar accepts only reviewed public REST venues, even when `--exchanges` is supplied. Its `observations.jsonl` file also rotates to one backup and is bounded by `--max-file-mb`. Keep the data directory private and provision disk space for other VST datasets separately.

## Safety and current limitations

- Discovery and public collection do not require exchange accounts or API keys.
- New candidate entries are unverified and do not become active adapters.
- The built-in native WebSocket capability labels are conservative and describe repository implementations, not a guarantee of current venue connectivity.
- The REST radar is public polling through CCXT; the separate native WebSocket collectors provide top-of-book and protocol-specific L2 streams for reviewed Binance, OKX and Coinbase mappings. None authenticates or accesses private account endpoints.
- No orders, transfers, deposits, withdrawals, conversions or investment actions are exposed by this discovery workflow.
- VST remains PAPER / observational-only. Physical-PC stability, actual endpoint availability and sustained data quality still require local validation.
