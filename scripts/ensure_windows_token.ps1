$ErrorActionPreference = "Stop"

$name = "VST_LOCAL_TOKEN"
$current = [Environment]::GetEnvironmentVariable($name, "User")
if ([string]::IsNullOrWhiteSpace($current)) {
    $bytes = New-Object byte[] 32
    [System.Security.Cryptography.RandomNumberGenerator]::Fill($bytes)
    $current = [Convert]::ToBase64String($bytes).Replace("+","-").Replace("/","_").TrimEnd("=")
    [Environment]::SetEnvironmentVariable($name, $current, "User")
    Write-Host "Generated a new local VST_LOCAL_TOKEN for this Windows user." -ForegroundColor Green
} else {
    Write-Host "Existing VST_LOCAL_TOKEN preserved." -ForegroundColor Green
}

Set-Item -Path "Env:$name" -Value $current
Write-Host "Local API authentication token is configured."
