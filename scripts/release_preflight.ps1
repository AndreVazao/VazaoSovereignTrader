$ErrorActionPreference = 'Stop'

$repo = Split-Path -Parent $PSScriptRoot
Set-Location $repo

Write-Host '=== VazaoSovereignTrader release preflight ===' -ForegroundColor Cyan

$checks = @(
    @{ Name = 'Git'; Command = 'git' },
    @{ Name = 'Python'; Command = 'python' },
    @{ Name = 'Inno Setup'; Command = 'iscc' },
    @{ Name = 'ADB'; Command = 'adb' }
)

foreach ($check in $checks) {
    $cmd = Get-Command $check.Command -ErrorAction SilentlyContinue
    if (-not $cmd) { throw "$($check.Name) is missing from PATH." }
    Write-Host "[OK] $($check.Name): $($cmd.Source)"
}

if (-not (Test-Path '.github\workflows\android-apk.yml')) { throw 'Android APK workflow missing.' }
if (-not (Test-Path '.github\workflows\windows-exe.yml')) { throw 'Windows build workflow missing.' }
if (-not (Test-Path 'MOBILE_APP\buildozer.spec')) { throw 'Buildozer spec missing.' }
if (-not (Test-Path 'installer\VazaoSovereignTrader.iss')) { throw 'Inno Setup script missing.' }

& python -m py_compile MOBILE_APP\main.py MOBILE_APP\secure_token.py
if ($LASTEXITCODE -ne 0) { throw 'Mobile Python compile check failed.' }

& python -m pytest -q tests\test_mobile_pairing.py tests\test_mobile_pairing_api.py tests\test_mobile_secure_token.py tests\test_controlled_restart_recovery_e2e.py tests\test_real_controlled_runtime_e2e.py
if ($LASTEXITCODE -ne 0) { throw 'Release-focused test checkpoint failed.' }

Write-Host ''
Write-Host '[READY] Windows installer toolchain is present.' -ForegroundColor Green
Write-Host '[READY] Android install toolchain is present (ADB).' -ForegroundColor Green
Write-Host '[INFO] Android APK build is intentionally performed by GitHub Actions on Ubuntu; Buildozer is not required natively on Windows.' -ForegroundColor Yellow
Write-Host ''
Write-Host 'Windows build: .\scripts\build_windows_installer.ps1' -ForegroundColor White
Write-Host 'Android build: trigger .github/workflows/android-apk.yml manually, then download the APK artifact.' -ForegroundColor White
Write-Host 'Android install: .\scripts\install_apk.ps1 -ApkPath <apk>' -ForegroundColor White
Write-Host 'PC install: run installer-output\VazaoSovereignTrader-Setup.exe' -ForegroundColor White