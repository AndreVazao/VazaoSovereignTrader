# VST supervised public market-data service

The Windows installer packages a headless supervisor and four fixed public-data workers:
- REST Market Radar
- WebSocket top-of-book collector
- WebSocket L2/order-book collector
- Existing WebSocket market-data/PAPER-learning collector

The supervisor is independent of the cockpit. It starts only binaries shipped in the same installation directory; it does not accept arbitrary commands or load exchange credentials. All collectors remain public-data/PAPER-only.

## Windows operation
1. Install VST using the normal installer.
2. From the Start Menu, select **Iniciar recolha contínua**.
3. Leave the service running; the cockpit can be closed.
4. To stop it cleanly, select **Parar recolha contínua**.

The uninstaller requests a cooperative service shutdown and waits up to 30 seconds before removing worker binaries. The service is not configured for automatic Windows logon startup in this milestone. Validate it on the target PC before enabling unattended startup.

## Data and health
Persistent data is stored outside the application directory so an application upgrade does not overwrite it:

`%LOCALAPPDATA%\VazaoSovereignTraderData\market-data\radar`

Supervisor health:
`%LOCALAPPDATA%\VazaoSovereignTraderData\market-data\market_data_service_health.json`

Supervisor log:
`%LOCALAPPDATA%\VazaoSovereignTraderData\market-data\logs\market_data_service.log`

The supervisor writes atomic health snapshots, checks each worker heartbeat, restarts exited/stale workers with exponential backoff, limits each worker to eight starts in a 15-minute window, and reports persistent storage usage against the aggregate budget. The service log rotates at 2 MiB with two backups. A singleton file lock prevents a second supervisor instance from launching duplicate collectors.

The collector JSONL files retain their individual bounded rotation policies. The supervisor enforces a **5 GiB (5,120 MiB) aggregate budget** across the persistent market-data directory by default (CLI range 1 MiB–5,120 MiB). It checks the budget before starting and during operation; if exhausted, it refuses startup or cooperatively stops all workers and records `storage_budget_exhausted` in health. At service startup it deletes only raw `.jsonl` files older than 30 days under the `radar` data directory; it does not delete JSON reports, configuration, logs or health records. Symlinks are excluded.

## Automatic evidence reports
The continuous Market Data worker refreshes the existing PAPER evidence pipeline automatically:
- First refresh: **60 minutes** after collector startup, allowing data to accumulate.
- Subsequent refreshes: every **6 hours** by default.
- Configurable via `radar.evidence_refresh_initial_delay_minutes` (5 minutes–24 hours) and `radar.evidence_refresh_interval_hours` (1–168 hours).
- Refresh work passes through the adaptive resource budget. If deferred or failed, it retries after 15 minutes and reports the state in `market_data_health.json`.
- Reports are written to their existing configured paths using atomic replacement. The latest report is retained; no unbounded archive is created. Each report carries its own generation timestamp where supported.
- The pipeline uses completed PAPER outcomes and fresh public top-of-book observations. Insufficient data remains explicitly insufficient; a positive PAPER result is not proof of profitability and does not authorize trading.

The scheduled refresh is part of the existing Market Data executable, so it does not introduce another continuously running process.

## Resource and safety boundaries
- Default symbols: BTC/USDT and ETH/USDT.
- No private exchange endpoints, API credentials, orders, transfers, or account mutations.
- No live trading authority; execution_authorized remains false.
- Workers are started without a shell and with standard input/output detached.
- Heavy PAPER study remains subject to the existing adaptive resource budget.
- The supervisor evaluates collector health timestamps, not just process liveness.

## Validation boundary
CI validates worker lifecycle, restart limits, health reporting, packaging, and the Windows installer workflow. It does not replace installation and long-running network validation on the owner's PC. Do not enable unattended startup or connect private exchange accounts until that local test is complete.