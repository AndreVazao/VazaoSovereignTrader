param(
    [Parameter(Mandatory = $true)]
    [string]$ApkPath,
    [switch]$SkipDeviceCheck
)

$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
Set-Location $repo

$adb = Get-Command adb -ErrorAction SilentlyContinue
if (-not $adb) { throw 'ADB not found. Install Android Platform Tools and reopen PowerShell.' }

$apk = (Resolve-Path $ApkPath -ErrorAction Stop).Path
if ([IO.Path]::GetExtension($apk).ToLowerInvariant() -ne '.apk') { throw 'ApkPath must point to an .apk file.' }

if (-not $SkipDeviceCheck) {
    $devices = @(adb devices | Select-String -Pattern '\tdevice$')
    if ($devices.Count -ne 1) {
        adb devices
        throw "Expected exactly one authorized Android device; found $($devices.Count)."
    }
}

Write-Host "Installing $apk ..." -ForegroundColor Cyan
& adb install -r $apk
if ($LASTEXITCODE -ne 0) { throw 'ADB APK installation failed.' }

Write-Host '[OK] APK installed.' -ForegroundColor Green
Write-Host 'Next: open Vazao Sovereign Trader on Android and complete the protected pairing flow.' -ForegroundColor White