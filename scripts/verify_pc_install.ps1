$ErrorActionPreference = "Stop"

$repo = Split-Path -Parent $PSScriptRoot
$python = Join-Path $repo "PC_ENGINE\.venv\Scripts\python.exe"
$config = Join-Path $repo "PC_ENGINE\config\config.local.json"
$report = Join-Path $repo "PC_ENGINE\data\logs\installation_health.json"

if (-not (Test-Path $python)) { throw "Virtual environment missing. Run scripts\setup_windows.ps1 first." }
if (-not (Test-Path $config)) { throw "config.local.json missing. Run scripts\setup_windows.ps1 first." }

& $python -m compileall -q (Join-Path $repo "PC_ENGINE")
if ($LASTEXITCODE -ne 0) { throw "Python compile check failed." }

& $python -c "import ccxt, flask, pydantic, requests, websocket, playwright; print('Python dependencies: OK')"
if ($LASTEXITCODE -ne 0) { throw "Required Python dependencies are missing." }

& $python -m playwright --version
if ($LASTEXITCODE -ne 0) { throw "Playwright runtime is not available." }

& $python -c "import json; from pathlib import Path; c=json.loads(Path(r'$config').read_text(encoding='utf-8')); assert str(c.get('mode','PAPER')).upper() == 'PAPER'; assert c.get('radar',{}).get('observational_only',True) is True; print('Config safety defaults: OK')"
if ($LASTEXITCODE -ne 0) { throw "Configuration safety checks failed." }

& $python -m pytest -q (Join-Path $repo "tests")
if ($LASTEXITCODE -ne 0) { throw "Python test suite failed." }

foreach ($dir in @((Join-Path $repo "PC_ENGINE\data\radar"), (Join-Path $repo "PC_ENGINE\data\browser\profiles"), (Join-Path $repo "PC_ENGINE\data\logs"))) {
    if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }
}

$tasks = @()
foreach ($taskName in @("VazaoSovereignTrader", "VazaoSovereignTrader-MarketData")) {
    try {
        $task = Get-ScheduledTask -TaskName $taskName -ErrorAction Stop
        $tasks += [ordered]@{"name"=$taskName; "state"=[string]$task.State; "installed"=$true}
    } catch {
        $tasks += [ordered]@{"name"=$taskName; "state"="NOT_INSTALLED"; "installed"=$false}
    }
}

$health = [ordered]@{
    schema_version = 1
    timestamp_utc = [DateTime]::UtcNow.ToString("o")
    repository = $repo
    python = [ordered]@{"path"=$python; "exists"=(Test-Path $python)}
    config = [ordered]@{"path"=$config; "exists"=(Test-Path $config); "paper_default"=$true}
    dependencies = "PASS"
    playwright = "PASS"
    python_tests = "PASS"
    scheduled_tasks = $tasks
    authenticated_api_token_present = [bool]$env:VST_LOCAL_TOKEN
    public_market_data_keys_required = $false
    paper_only_verification = $true
}
$health | ConvertTo-Json -Depth 8 | Set-Content -Path $report -Encoding UTF8

if (-not $env:VST_LOCAL_TOKEN) {
    Write-Warning "VST_LOCAL_TOKEN is not set in this PowerShell session. The engine API will refuse authenticated commands until it is configured."
}

Write-Host "PC verification completed successfully." -ForegroundColor Green
Write-Host "Installation health report: $report"
