$ErrorActionPreference = "Stop"

$repo = Split-Path -Parent $PSScriptRoot
$pc = Join-Path $repo "PC_ENGINE"
$venv = Join-Path $pc ".venv"
$python = Join-Path $venv "Scripts\python.exe"
$configDir = Join-Path $pc "config"
$config = Join-Path $configDir "config.local.json"
$configExample = Join-Path $configDir "config.example.json"

if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    throw "Python launcher 'py' was not found. Install Python 3.11+ first."
}

if (-not (Test-Path $python)) {
    py -3 -m venv $venv
    if ($LASTEXITCODE -ne 0) { throw "Python virtual environment creation failed." }
}
if (-not (Test-Path $python)) {
    throw "Python virtual environment was not created: $python"
}

& $python -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw "Python pip upgrade failed." }

& $python -m pip install -r (Join-Path $repo "requirements-pc.txt")
if ($LASTEXITCODE -ne 0) { throw "PC runtime dependency installation failed." }

& $python -m playwright install chromium
if ($LASTEXITCODE -ne 0) { throw "Playwright Chromium installation failed." }

$runtimeDirs = @(
    (Join-Path $pc "data\radar"),
    (Join-Path $pc "data\browser\profiles"),
    (Join-Path $pc "data\logs")
)
New-Item -ItemType Directory -Force -Path $runtimeDirs | Out-Null

if (-not (Test-Path $config)) {
    Copy-Item $configExample $config
}

Write-Host ""
Write-Host "VazaoSovereignTrader PC runtime READY." -ForegroundColor Green
Write-Host "Installed: Python environment, dependencies, Chromium and data directories."
Write-Host "Default mode: PAPER. Public market-data collection requires no exchange API key."
Write-Host ""
Write-Host "Next steps:"
Write-Host "  1. Generate a local token if missing: scripts\ensure_windows_token.ps1"
Write-Host "     Optional: set a chosen token with scripts\configure_windows_secrets.ps1"
Write-Host "  2. Verify installation with scripts\verify_pc_install.ps1"
Write-Host "  3. Verify public market data with scripts\verify_public_market_data.ps1"
Write-Host "  4. Start manually with scripts\windows_run_pc_engine.bat"
Write-Host "  5. Optional source-checkout autostart only after local validation: scripts\install_windows_autostart.ps1"
Write-Host ""
