param(
    [switch]$RunTests,
    [string]$TestPath = "tests"
)

$ErrorActionPreference = "Stop"

$repo = Split-Path -Parent $PSScriptRoot
$engine = Join-Path $repo "PC_ENGINE"
$python = Join-Path $engine ".venv\Scripts\python.exe"
$config = Join-Path $engine "config\config.local.json"
$report = Join-Path $engine "data\logs\installation_health.json"

if (-not (Test-Path $python)) { throw "Virtual environment missing. Run scripts\setup_windows.ps1 first." }
if (-not (Test-Path $config)) { throw "config.local.json missing. Run scripts\setup_windows.ps1 first." }

# Compile only first-party Python files. Never recurse into .venv or installed packages.
$compileScript = @'
import pathlib
import py_compile
import sys

root = pathlib.Path(sys.argv[1])
excluded = {".venv", "venv", "__pycache__", ".git", "node_modules"}
files = [
    path for path in root.rglob("*.py")
    if not any(part in excluded for part in path.relative_to(root).parts)
]
for path in files:
    py_compile.compile(str(path), doraise=True)
print(f"Compiled {len(files)} first-party Python files.")
'@
& $python -c $compileScript $engine
if ($LASTEXITCODE -ne 0) { throw "First-party Python compile check failed." }

& $python -c "import ccxt, flask, pydantic, requests, websocket, playwright; print('Python runtime dependencies: OK')"
if ($LASTEXITCODE -ne 0) { throw "Required Python runtime dependencies are missing." }

if (-not (Test-Path (Join-Path $engine "tools\run_market_data_bootstrap.py"))) {
    throw "Public market-data bootstrap tool is missing."
}
if (-not (Test-Path (Join-Path $engine "tools\run_market_data_collector.py"))) {
    throw "Continuous market-data collector is missing."
}
& $python -m playwright --version
if ($LASTEXITCODE -ne 0) { throw "Playwright runtime is not available." }

& $python -c "import json,sys; from pathlib import Path; c=json.loads(Path(sys.argv[1]).read_text(encoding='utf-8')); assert str(c.get('mode','PAPER')).upper() == 'PAPER'; assert c.get('radar',{}).get('observational_only',True) is True; a=c.get('autonomous_execution',{}); assert a.get('allow_real',False) is False; assert a.get('auto_promote_real',False) is False; print('PAPER safety configuration: OK')" $config
if ($LASTEXITCODE -ne 0) { throw "Configuration safety checks failed. REAL execution and automatic promotion must remain disabled." }

$pythonTests = "SKIPPED_NOT_REQUESTED"
if ($RunTests) {
    & $python -c "import pytest" 2>$null
    if ($LASTEXITCODE -ne 0) {
        throw "pytest is not installed in the runtime environment. Install development dependencies with: .venv\Scripts\python.exe -m pip install -r requirements-dev.txt"
    }
    $resolvedTestPath = Join-Path $repo $TestPath
    if (-not (Test-Path $resolvedTestPath)) { throw "Test path not found: $resolvedTestPath" }
    & $python -m pytest -q $resolvedTestPath
    if ($LASTEXITCODE -ne 0) { throw "Requested Python tests failed." }
    $pythonTests = "PASS"
}

foreach ($dir in @((Join-Path $engine "data\radar"), (Join-Path $engine "data\browser\profiles"), (Join-Path $engine "data\logs"))) {
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
    schema_version = 2
    timestamp_utc = [DateTime]::UtcNow.ToString("o")
    repository = $repo
    python = [ordered]@{"path"=$python; "exists"=(Test-Path $python)}
    config = [ordered]@{"path"=$config; "exists"=(Test-Path $config); "paper_default"=$true}
    dependencies = "PASS"
    playwright = "PASS"
    first_party_compile = "PASS"
    python_tests = $pythonTests
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
Write-Host "Python tests: $pythonTests"
Write-Host "Installation health report: $report"
