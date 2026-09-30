$ErrorActionPreference = "Stop"

$repo = Split-Path -Parent $PSScriptRoot
$python = Join-Path $repo "PC_ENGINE\.venv\Scripts\python.exe"
$entry = Join-Path $repo "PC_ENGINE\main.py"
$collector = Join-Path $repo "PC_ENGINE\tools\run_market_data_collector.py"
$config = Join-Path $repo "PC_ENGINE\config\config.local.json"
$dataDir = Join-Path $repo "PC_ENGINE\data\radar"
$logDir = Join-Path $repo "PC_ENGINE\data\logs"

if (-not (Test-Path $python)) {
    throw "Python virtual environment not found: $python"
}
if (-not (Test-Path $config)) {
    throw "config.local.json not found. Run scripts\setup_windows.ps1 first."
}
New-Item -ItemType Directory -Force -Path $logDir, $dataDir | Out-Null

$trigger = New-ScheduledTaskTrigger -AtStartup
$settings = New-ScheduledTaskSettingsSet -RestartCount 20 -RestartInterval (New-TimeSpan -Minutes 1) -StartWhenAvailable -ExecutionTimeLimit ([TimeSpan]::Zero)

$engineAction = New-ScheduledTaskAction -Execute $python -Argument ('"' + $entry + '"') -WorkingDirectory $repo
$collectorAction = New-ScheduledTaskAction -Execute $python -Argument ('"' + $collector + '" --config "' + $config + '" --data-dir "' + $dataDir + '"') -WorkingDirectory $repo

Register-ScheduledTask -TaskName "VazaoSovereignTrader" -Action $engineAction -Trigger $trigger -Settings $settings -Description "Starts VazaoSovereignTrader PC engine at Windows startup." -Force | Out-Null
Register-ScheduledTask -TaskName "VazaoSovereignTrader-MarketData" -Action $collectorAction -Trigger $trigger -Settings $settings -Description "Starts VazaoSovereignTrader public WebSocket market-data collection at Windows startup." -Force | Out-Null

Write-Host "Scheduled tasks installed:" -ForegroundColor Green
Write-Host "  VazaoSovereignTrader"
Write-Host "  VazaoSovereignTrader-MarketData"
Write-Host "Both tasks are PAPER/observational only at startup."
