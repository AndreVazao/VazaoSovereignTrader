$ErrorActionPreference = "Stop"

$repo = Split-Path -Parent $PSScriptRoot
$python = Join-Path $repo "PC_ENGINE\.venv\Scripts\python.exe"
$entry = Join-Path $repo "PC_ENGINE\main.py"
$logDir = Join-Path $repo "PC_ENGINE\data\logs"

if (-not (Test-Path $python)) {
    throw "Python virtual environment not found: $python"
}
New-Item -ItemType Directory -Force -Path $logDir | Out-Null

$action = New-ScheduledTaskAction -Execute $python -Argument ('"' + $entry + '"') -WorkingDirectory (Join-Path $repo "PC_ENGINE")
$trigger = New-ScheduledTaskTrigger -AtStartup
$settings = New-ScheduledTaskSettingsSet -RestartCount 20 -RestartInterval (New-TimeSpan -Minutes 1) -StartWhenAvailable -ExecutionTimeLimit ([TimeSpan]::Zero)

Register-ScheduledTask -TaskName "VazaoSovereignTrader" -Action $action -Trigger $trigger -Settings $settings -Description "Starts VazaoSovereignTrader PC engine at Windows startup." -Force | Out-Null

Write-Host "Scheduled task installed: VazaoSovereignTrader"
