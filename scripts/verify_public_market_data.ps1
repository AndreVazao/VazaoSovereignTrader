$ErrorActionPreference = "Stop"

$repo = Split-Path -Parent $PSScriptRoot
$python = Join-Path $repo "PC_ENGINE.venvScriptspython.exe"
$config = Join-Path $repo "PC_ENGINEconfigconfig.local.json"

if (-not (Test-Path $python)) {
    throw "Virtual environment missing. Run scriptssetup_windows.ps1 first."
}
if (-not (Test-Path $config)) {
    throw "config.local.json missing. Run scriptssetup_windows.ps1 first."
}

Write-Host "Checking public market-data connectivity and OHLCV quality..." -ForegroundColor Cyan
& $python (Join-Path $repo "PC_ENGINE	oolsun_market_data_bootstrap.py") --config $config
if ($LASTEXITCODE -ne 0) {
    throw "Public market-data bootstrap failed or is degraded. Check network/exchange availability and the report in PC_ENGINEdataadarmarket_data_bootstrap.json."
}

Write-Host ""
Write-Host "Public market-data bootstrap: READY" -ForegroundColor Green
Write-Host "The trader can now be started in PAPER mode and the continuous WebSocket collector can be installed with scriptsinstall_windows_autostart.ps1."
