$ErrorActionPreference = "Stop"

$repo = Split-Path -Parent $PSScriptRoot
$pc = Join-Path $repo "PC_ENGINE"
Set-Location $pc

if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    throw "Python launcher 'py' was not found. Install Python 3.11+ first."
}

if (-not (Test-Path ".venv")) {
    py -3 -m venv .venv
}

$python = Join-Path $pc ".venv\Scripts\python.exe"
& $python -m pip install --upgrade pip
& $python -m pip install -r (Join-Path $repo "requirements-pc.txt")
& $python -m playwright install chromium

New-Item -ItemType Directory -Force -Path (Join-Path $pc "data\radar"), (Join-Path $pc "data\browser\profiles"), (Join-Path $pc "data\logs") | Out-Null

if (-not (Test-Path "config\config.local.json")) {
    Copy-Item "config\config.example.json" "config\config.local.json"
}

Write-Host ""
Write-Host "VazaoSovereignTrader PC runtime READY." -ForegroundColor Green
Write-Host "Installed: Python environment, dependencies, Chromium and data directories."
Write-Host "Default mode: PAPER. Public market-data collection requires no exchange API key."
Write-Host ""
Write-Host "Next steps:"
Write-Host "  1. Set VST_LOCAL_TOKEN with scripts\configure_windows_secrets.ps1"
Write-Host "  2. Verify installation with scripts\verify_pc_install.ps1"
Write-Host "  3. Verify public market data with scripts\verify_public_market_data.ps1"
Write-Host "  4. Install 24/7 startup with scripts\install_windows_autostart.ps1"
Write-Host ""
