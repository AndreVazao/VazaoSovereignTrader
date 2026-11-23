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
while ((Get-Date) -lt $deadline) {
    try {
        if (Test-Path -LiteralPath $healthPath) {
            $health = Get-Content -LiteralPath $healthPath -Raw | ConvertFrom-Json
            if ($health.status -eq "STOPPED") {
                Remove-Item -LiteralPath $stopRequest -Force -ErrorAction SilentlyContinue
                break
            }
        }
    } catch { }
    Start-Sleep -Seconds 1
}
Write-Host "Pedido de paragem enviado; aguardado até 30 segundos."
