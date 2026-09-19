$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot
$pc = Join-Path $repo "PC_ENGINE"
Set-Location $pc
if (-not (Get-Command py -ErrorAction SilentlyContinue)) { throw "Python launcher py was not found. Install Python 3.11+ first." }
if (-not (Test-Path ".venv")) { py -3 -m venv .venv }
$python = Join-Path $pc ".venv\Scripts\python.exe"
& $python -m pip install --upgrade pip
& $python -m pip install -r (Join-Path $repo "requirements-pc.txt")
& $python -m playwright install chromium
New-Item -ItemType Directory -Force -Path (Join-Path $pc "data\radar"), (Join-Path $pc "data\browser\profiles"), (Join-Path $pc "logs") | Out-Null
if (-not (Test-Path "config\config.local.json")) { Copy-Item "config\config.example.json" "config\config.local.json" }
Write-Host "VazaoSovereignTrader PC runtime READY."
Write-Host "Start data collection with scripts\start_market_data_collector.bat"