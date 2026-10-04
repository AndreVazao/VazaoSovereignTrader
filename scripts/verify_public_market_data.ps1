$ErrorActionPreference = "Stop"

$repo = Split-Path -Parent $PSScriptRoot
$python = Join-Path $repo "PC_ENGINE\.venv\Scripts\python.exe"
$config = Join-Path $repo "PC_ENGINE\config\config.local.json"
$dataDir = Join-Path $repo "PC_ENGINE\data\radar"
$report = Join-Path $dataDir "market_data_bootstrap.json"

if (-not (Test-Path $python)) {
    throw "Virtual environment missing. Run scripts\setup_windows.ps1 first."
}
if (-not (Test-Path $config)) {
    throw "config.local.json missing. Run scripts\setup_windows.ps1 first."
}

Write-Host "Checking public market-data connectivity and OHLCV quality..." -ForegroundColor Cyan
& $python (Join-Path $repo "PC_ENGINE\tools\run_market_data_bootstrap.py") --config $config --data-dir $dataDir
if ($LASTEXITCODE -ne 0) {
    throw "Public market-data bootstrap failed or is degraded. Check network/exchange availability and $report."
}

if (-not (Test-Path $report)) {
    throw "Bootstrap returned success but did not create its expected report: $report"
}

try {
    $result = Get-Content -LiteralPath $report -Raw | ConvertFrom-Json
} catch {
    throw "Bootstrap report is not valid JSON: $report"
}
if ($result.status -ne "READY") {
    throw "Bootstrap report is not READY. Inspect venue/symbol errors in $report."
}

Write-Host ""
Write-Host "Public market-data bootstrap: READY" -ForegroundColor Green
Write-Host "Report: $report"
Write-Host "The check uses public/read-only market data; no exchange API keys are required."
Write-Host "To begin continuous PAPER/observational collection, run scripts\install_windows_autostart.ps1."
