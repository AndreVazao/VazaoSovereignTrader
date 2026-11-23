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

The collector JSONL files retain their individual bounded rotation policies. In addition, the supervisor enforces a 1 GiB aggregate budget across the persistent market-data directory by default (configurable from 1 MiB to 8 GiB when launching the service directly). It checks the budget before starting and during operation; if exhausted, it refuses startup or cooperatively stops all workers and records `storage_budget_exhausted` in health. It does not delete market history automatically. The usage scan does not follow symlinks.

## Resource and safety boundaries
- Default symbols: BTC/USDT and ETH/USDT.
- No private exchange endpoints, API credentials, orders, transfers, or account mutations.
- No live trading authority; execution_authorized remains false.
- Workers are started without a shell and with standard input/output detached.
- Heavy PAPER study remains subject to the existing adaptive resource budget.
- The supervisor evaluates collector health timestamps, not just process liveness.

## Validation boundary
CI validates worker lifecycle, restart limits, health reporting, packaging, and the Windows installer workflow. It does not replace installation and long-running network validation on the owner's PC. Do not enable unattended startup or connect private exchange accounts until that local test is complete.