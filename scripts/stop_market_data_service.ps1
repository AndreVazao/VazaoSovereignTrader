$ErrorActionPreference = "Stop"
$dataRoot = Join-Path $env:LOCALAPPDATA "VazaoSovereignTraderData\market-data"
$healthPath = Join-Path $dataRoot "market_data_service_health.json"
$stopRequest = Join-Path $dataRoot "stop.request"
New-Item -ItemType Directory -Force -Path $dataRoot | Out-Null
if (Test-Path -LiteralPath $stopRequest) {
    $existing = Get-Item -LiteralPath $stopRequest -Force
    if (($existing.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw "Stop request path cannot be a reparse point." }
}
Set-Content -LiteralPath $stopRequest -Value "stop" -NoNewline -Encoding ascii
if (Test-Path -LiteralPath $healthPath) {
    $deadline = (Get-Date).AddSeconds(30)
    while ((Get-Date) -lt $deadline) {
        try {
            $health = Get-Content -LiteralPath $healthPath -Raw | ConvertFrom-Json
            if ($health.status -eq "STOPPED") { break }
        } catch { }
        Start-Sleep -Seconds 1
    }
}
Write-Host "Pedido de paragem enviado; o serviço foi aguardado até 30 segundos."
