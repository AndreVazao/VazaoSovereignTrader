$ErrorActionPreference = "Stop"
$dataRoot = Join-Path $env:LOCALAPPDATA "VazaoSovereignTraderData\market-data"
New-Item -ItemType Directory -Force -Path $dataRoot | Out-Null
$stopRequest = Join-Path $dataRoot "stop.request"
Set-Content -LiteralPath $stopRequest -Value "stop" -NoNewline -Encoding ascii
Write-Host "Pedido de paragem enviado ao serviço de recolha VST."
