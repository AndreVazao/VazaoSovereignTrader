$ErrorActionPreference = "Stop"

$repo = Split-Path -Parent $PSScriptRoot
$python = Join-Path $repo "PC_ENGINE\.venv\Scripts\python.exe"

if (-not (Test-Path $python)) { throw "Virtual environment missing. Run scripts/setup_windows.ps1 first." }

& $python -m compileall -q (Join-Path $repo "PC_ENGINE")
& $python -m pytest -q (Join-Path $repo "tests")

if (-not $env:VST_LOCAL_TOKEN) {
    Write-Warning "VST_LOCAL_TOKEN is not set in this PowerShell session."
}

Write-Host "PC verification completed."
