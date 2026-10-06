[CmdletBinding()]
param(
    [ValidateSet("python", "shared-learning", "windows", "android", "all")]
    [string]$Scope = "python"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $root

function Invoke-Checked {
    param([string]$Command, [string[]]$Arguments)
    Write-Host ">> $Command $($Arguments -join ' ')"
    & $Command @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed with exit code ${LASTEXITCODE}: $Command"
    }
}

if ($Scope -in @("python", "all")) {
    if (-not (Get-Command python -ErrorAction SilentlyContinue)) { throw "Python was not found on PATH." }
    Invoke-Checked "python" @("-m", "pytest", "-q", "tests")
}

if ($Scope -in @("shared-learning", "all")) {
    if (-not (Get-Command npm -ErrorAction SilentlyContinue)) { throw "npm was not found on PATH." }
    Push-Location (Join-Path $root "cloud/shared-learning")
    try {
        Invoke-Checked "npm" @("install")
        Invoke-Checked "npm" @("test")
        Invoke-Checked "npm" @("run", "build")
    } finally { Pop-Location }
}

if ($Scope -in @("windows", "all")) {
    if (-not (Test-Path (Join-Path $root "scripts/build_windows_installer.ps1"))) { throw "Windows installer build script is missing." }
    & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $root "scripts/build_windows_installer.ps1")
    if ($LASTEXITCODE -ne 0) { throw "Windows installer build failed with exit code ${LASTEXITCODE}." }
}

if ($Scope -eq "android") {
    Write-Warning "Android APK validation is not part of the normal Windows local default. Use a configured Android/WSL environment or the manual GitHub workflow."
    exit 0
}

Write-Host "Local validation completed successfully for scope '$Scope'."
