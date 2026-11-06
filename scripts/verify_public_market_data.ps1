param(
    [switch]$RequireAllExchanges,
    [ValidateRange(1, 100)]
    [int]$MinimumReadyVenues = 1
)

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
$bootstrapArgs = @("--config", $config, "--data-dir", $dataDir)
if ($RequireAllExchanges) {
    $bootstrapArgs += "--require-all-exchanges"
} else {
    $bootstrapArgs += @("--minimum-ready-venues", [string]$MinimumReadyVenues)
}
& $python (Join-Path $repo "PC_ENGINE\tools\run_market_data_bootstrap.py") @bootstrapArgs
if ($LASTEXITCODE -ne 0) {
    throw "Public market-data bootstrap failed or did not meet its readiness threshold. Check venue/symbol diagnostics in $report."
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

$readyCount = [int]$result.ready_venues
$totalCount = [int]$result.total_venues
Write-Host ""
Write-Host "Public market-data bootstrap: READY ($readyCount/$totalCount venues fully ready)" -ForegroundColor Green
if (-not [bool]$result.all_configured_venues_ready) {
    $degraded = @($result.degraded_venues)
    if ($degraded.Count -gt 0) {
        Write-Warning ("Some configured venues are partial or unavailable: " + ($degraded -join ", "))
    }
    if (-not $RequireAllExchanges) {
        Write-Warning "The minimum ready-venue threshold was met. Cross-venue research remains limited until additional venues become healthy."
    }
}
Write-Host "Report: $report"
Write-Host "The check uses public/read-only market data; no exchange API keys are required."
Write-Host "To begin continuous PAPER/observational collection, run scripts\install_windows_autostart.ps1."
