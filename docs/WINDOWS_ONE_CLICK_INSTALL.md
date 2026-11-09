# Windows One-Click Installer

The Windows package is distributed as a single Inno Setup installer produced by the `Windows EXE` GitHub Actions workflow.

## What the installer does

1. Installs the frozen PC engine and public market-data collector executables.
2. Creates the local configuration and runtime directories.
3. Creates persistent operator exchange folders:
   - `data/operator_exchange/INBOX` — files sent from the mobile cockpit/operator to the PC.
   - `data/operator_exchange/OUTBOX` — reports and artefacts prepared by the PC for download.
4. Creates desktop and Start Menu shortcuts.
5. Keeps the existing local configuration when upgrading an installation.

The installer is user-local and does not require administrator elevation.

## What the installer deliberately does not do

- It does not start the engine after installation.
- It does not start the Market Data collector.
- It does not register Windows scheduled tasks.
- It does not enable unattended startup or restart policies.

This manual-first behavior is intentional. The operator must inspect the configuration, validate the local installation and health endpoint, and explicitly start each service. The installer must never begin unattended activity before that validation.

## Runtime locations

Application install root:

`%LOCALAPPDATA%\\VazaoSovereignTrader`

Local configuration:

`%LOCALAPPDATA%\\VazaoSovereignTrader\\config\\config.local.json`

Default radar data directory:

`%LOCALAPPDATA%\\VazaoSovereignTrader\\data\\radar`

The durable learning vault is stored separately from the application binaries. The Windows installer lifecycle test verifies that a vault marker under `%LOCALAPPDATA%\\VazaoSovereignTraderData\\vault` retains the same SHA-256 across installation, in-place upgrade and uninstall.

## Safety and first validation

The current installation and validation phase is PAPER-only:

- Keep `mode=PAPER`.
- Keep `autonomous_execution.allow_real=false` and `autonomous_execution.auto_promote_real=false`.
- Public market-data collection does not require exchange API keys.
- Do not add private exchange credentials or trading permissions for initial installation or PAPER validation.
- `VST_LOCAL_TOKEN` is the local API control token; it is not an exchange credential.

Before starting the engine, inspect `config\\config.local.json`. Set `VST_LOCAL_TOKEN` as a Windows user environment variable before using authenticated API operations. The unauthenticated `GET /health` endpoint can be used for the basic health check.

Launch the engine manually using the desktop/Start Menu shortcut, then verify:

`http://127.0.0.1:8765/health`

Authenticated status and control endpoints require the local token.

## Bounded public collector validation

From PowerShell:

```powershell
Set-Location "$env:LOCALAPPDATA\\VazaoSovereignTrader"
.\\VazaoSovereignTrader-MarketData.exe --config ".\\config\\config.local.json" --data-dir ".\\data\\radar" --run-seconds 120
```

The bounded run exits through the collector's normal cleanup path and writes a final STOPPED health state. Inspect:

`data\\radar\\market_data_health.json`

After the bounded test succeeds, the collector can be started manually without `--run-seconds` for continuous observation. Do not configure unattended startup during the initial validation.

## Source-checkout autostart is a separate opt-in

`scripts/install_windows_autostart.ps1` applies only to a source checkout with its Python virtual environment and local configuration. It creates two Windows startup tasks. Run it only after successful local validation and an explicit operator decision. It is not included in or invoked by the packaged installer.

## Updating and uninstalling

A newer installer can be installed over the same application location. Existing `config.local.json` and user data are preserved. Uninstall removes application binaries and cleans up legacy VST scheduled tasks left by older installer versions; it does not delete the separate learning vault.

The CI lifecycle test performs a silent v1 install, silent in-place v2 upgrade, engine launch, HTTP health check, silent uninstall and SHA-256 verification of the vault marker. This is CI evidence; it does not replace validation on the target PC.

Do not expose the PC API with a router port-forward. Use an authenticated private network path when remote access is introduced and validated.
