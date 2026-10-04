# Windows One-Click Installer

The Windows release is distributed as a single Inno Setup installer.

## What the installer does

1. Installs the frozen PC engine and public market-data collector executables.
2. Creates the local configuration and runtime directories.
3. Creates persistent PAPER-only operator exchange folders:
   - `data/operator_exchange/INBOX` — files sent from the mobile cockpit/operator to the PC.
   - `data/operator_exchange/OUTBOX` — reports and artefacts prepared by the PC for download.
4. Registers two Windows logon tasks:
   - `VazaoSovereignTrader`
   - `VazaoSovereignTrader-MarketData`
5. Starts the PC engine after installation.
6. Keeps credentials outside the installer and outside the repository.

The installer is intentionally user-local and does not require administrator elevation.

## Runtime location

Default install root:

`%LOCALAPPDATA%\VazaoSovereignTrader`

Operator exchange:

`%LOCALAPPDATA%\VazaoSovereignTrader\data\operator_exchange\`

The API exposes the same exchange through authenticated endpoints so the Android cockpit can list, upload to INBOX, and download files from OUTBOX without exposing the entire filesystem.

## Safety

The packaged runtime remains PAPER/read-only for market-data collection. The installer does not create exchange credentials, does not submit orders, and does not enable a live execution path.

## Updating

A later installer can be installed over the same location. Runtime data and operator exchange files remain in place. Configuration is created from `config.example.json` only when `config.local.json` does not already exist.

## First launch and public-data collection

On the final setup page, leave **“Iniciar recolha de dados de mercado (PAPER) agora”** selected to start the scheduled public-data collector immediately. The installer also registers the collector to start at the next Windows logon. The collector uses public market endpoints; exchange API keys are not required for this phase.

Default data directory:

`%LOCALAPPDATA%\VazaoSovereignTrader\data\radar`

Useful local health and learning artefacts include:

- `market_data_health.json` — collector state and recent exchange connection health.
- `observations.jsonl` — market observations.
- `lead_lag_learning.jsonl` — PAPER analysis of cross-exchange timing relationships.
- `hot_path_outcomes.jsonl` — PAPER outcomes used for calibration.

Allow the collector to run for a while before interpreting learning outputs; early samples are not evidence of a profitable or executable edge. The collector is observational/PAPER-only and does not submit orders.

To inspect the scheduled tasks in PowerShell:

```powershell
Get-ScheduledTask -TaskName "VazaoSovereignTrader","VazaoSovereignTrader-MarketData" |
  Select-Object TaskName, State
```

If the collector does not start, inspect Task Scheduler history and the files under the radar data directory. Do not expose the PC API with a router port-forward.
