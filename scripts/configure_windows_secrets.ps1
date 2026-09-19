$ErrorActionPreference = "Stop"

$token = Read-Host "VST_LOCAL_TOKEN (long random token)"
if ([string]::IsNullOrWhiteSpace($token)) { throw "Token cannot be empty." }
[Environment]::SetEnvironmentVariable("VST_LOCAL_TOKEN", $token, "User")

$binanceKey = Read-Host "BINANCE_KEY (leave empty to skip)"
$binancePrivate = Read-Host "BINANCE_PRIVATE (leave empty to skip)"
if ($binanceKey) { [Environment]::SetEnvironmentVariable("BINANCE_KEY", $binanceKey, "User") }
if ($binancePrivate) { [Environment]::SetEnvironmentVariable("BINANCE_PRIVATE", $binancePrivate, "User") }

Write-Host "Secrets stored as Windows user environment variables."
Write-Host "Withdraw permission must remain disabled. Futures/leverage must remain disabled."
Write-Host "Close this terminal and open a new one before starting the engine."
