# PC install + continuous learning data collection

## Objective and current safety scope

The PC installation prepares VST for public market-data collection, local research and PAPER validation. The current development and installation phase is PAPER-only. Do not configure private exchange API keys, trading permissions or LIVE/REAL execution.

Public market-data collection does not require exchange API keys.

## Source installation on Windows

Run from the repository root:

```powershell
powershell -ExecutionPolicy Bypass -File .\\scripts\\setup_windows.ps1
powershell -ExecutionPolicy Bypass -File .\\scripts\\configure_windows_secrets.ps1
```

The secrets helper configures only the local API control token `VST_LOCAL_TOKEN`; it does not ask for or store exchange credentials. Close and reopen PowerShell after setting the user environment variable.

Run lightweight verification:

```powershell
powershell -ExecutionPolicy Bypass -File .\\scripts\\verify_pc_install.ps1
powershell -ExecutionPolicy Bypass -File .\\scripts\\verify_public_market_data.ps1
```

The installation verifier compiles first-party Python, checks runtime dependencies, Playwright and PAPER safety. It does not run the full Python test suite unless `-RunTests` is explicitly supplied. The public-data check uses read-only endpoints and records per-venue readiness in `market_data_bootstrap.json`.

Start the engine manually after validation:

```powershell
.\\scripts\\windows_run_pc_engine.bat
```

## Packaged Windows installer

The Inno Setup package installs the engine and public collector binaries, configuration and data directories, and shortcuts. It deliberately does not start either executable, create scheduled tasks or enable autostart. Inspect the local configuration and start services manually after validation. See `WINDOWS_ONE_CLICK_INSTALL.md` for the packaged lifecycle.

## Bounded collector validation

For a graceful, time-bounded source-checkout test:

```powershell
.\\PC_ENGINE\\.venv\\Scripts\\python.exe .\\PC_ENGINE\\tools\\run_market_data_collector.py --run-seconds 120
```

The collector exits through its normal cleanup path and writes a STOPPED health state. After the bounded test succeeds, it can be started manually in continuous mode by omitting `--run-seconds`.

## Optional autostart

Do not configure autostart during initial validation. For source checkouts only, `scripts/install_windows_autostart.ps1` creates two Windows startup tasks for the engine and public Market Data collector. Run it only after successful physical validation and an explicit operator decision. It is not part of the packaged installer.

## Local artefacts

- `PC_ENGINE/data/radar/websocket_events.jsonl` — normalized public tape.
- `PC_ENGINE/data/radar/websocket_lead_lag.jsonl` — cross-venue candidates.
- `PC_ENGINE/data/radar/websocket_latency_edges.jsonl` — observational timing measurements.
- `PC_ENGINE/data/radar/lead_lag_learning.json` — aggregated PAPER learning.
- `PC_ENGINE/data/radar/state_signature_learning.jsonl` and `state_outcomes.jsonl` — PAPER learning outputs.
- `PC_ENGINE/data/radar/market_data_health.json` — collector health and final state.

The collector does not submit orders or move funds. The research pipeline is:

`collect public data -> learn descriptively -> validate out-of-sample -> assess PAPER outcomes`

No result authorizes live trading or changes financial permissions.
