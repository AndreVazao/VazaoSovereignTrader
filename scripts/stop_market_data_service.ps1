$ErrorActionPreference = "Stop"
$dataRoot = Join-Path $env:LOCALAPPDATA "VazaoSovereignTraderData\market-data"
$healthPath = Join-Path $dataRoot "market_data_service_health.json"
$lockPath = Join-Path $dataRoot "service.lock"
$stopRequest = Join-Path $dataRoot "stop.request"
if (-not (Test-Path -LiteralPath $healthPath) -and -not (Test-Path -LiteralPath $lockPath)) { exit 0 }
if (Test-Path -LiteralPath $stopRequest) {
    $existing = Get-Item -LiteralPath $stopRequest -Force
    if (($existing.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw "Stop request path cannot be a reparse point." }
}
Set-Content -LiteralPath $stopRequest -Value "stop" -NoNewline -Encoding ascii
$deadline = (Get-Date).AddSeconds(30)
$stopped = $false
while ((Get-Date) -lt $deadline) {
    try {
        if (Test-Path -LiteralPath $healthPath) {
            $health = Get-Content -LiteralPath $healthPath -Raw | ConvertFrom-Json
            if ($health.status -eq "STOPPED") {
                $stopped = $true
                Remove-Item -LiteralPath $stopRequest -Force -ErrorAction SilentlyContinue
                break
            }
            if ($health.shutdown_reason -eq "worker_shutdown_timeout") {
                throw "Market-data workers did not stop within the supervisor shutdown budget."
            }
        }
    } catch {
        if ($_.Exception.Message -like "*did not stop within the supervisor shutdown budget*") { throw }
    }
    Start-Sleep -Seconds 1
}
if (-not $stopped) {
    throw "Market-data supervisor did not confirm STOPPED within 30 seconds; do not remove worker files."
}
Write-Host "Recolha contínua parada e confirmada."
