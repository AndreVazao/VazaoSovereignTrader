$ErrorActionPreference = "Stop"

$repo = Split-Path -Parent $PSScriptRoot
Set-Location (Join-Path $repo "PC_ENGINE")

if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    throw "Python launcher 'py' was not found. Install Python 3.11+ first."
}

if (-not (Test-Path ".venv")) {
    py -3 -m venv .venv
}

& ".\.venv\Scripts\python.exe" -m pip install --upgrade pip
& ".\.venv\Scripts\python.exe" -m pip install -r "..\requirements-pc.txt"

if (-not (Test-Path "config\config.local.json")) {
    Copy-Item "config\config.example.json" "config\config.local.json"
}

Write-Host "PC engine environment ready."
Write-Host "Set VST_LOCAL_TOKEN before starting:"
Write-Host '  $env:VST_LOCAL_TOKEN = "choose-a-long-random-secret"'
Write-Host "Then run: .\main.py"
