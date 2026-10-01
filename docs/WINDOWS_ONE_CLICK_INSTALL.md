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
