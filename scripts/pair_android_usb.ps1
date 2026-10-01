[CmdletBinding()]
param(
    [string]$ApkPath
)

$ErrorActionPreference = "Stop"

function Resolve-Adb {
    $command = Get-Command adb -ErrorAction SilentlyContinue
    if ($command) { return $command.Source }

    $candidates = @(
        (Join-Path $env:LOCALAPPDATA "Android\Sdk\platform-tools\adb.exe"),
        (Join-Path $env:ProgramFiles "Android\platform-tools\adb.exe")
    ) | Where-Object { $_ -and (Test-Path $_) }

    if ($candidates.Count -gt 0) { return $candidates[0] }
    throw "ADB não encontrado. Instala Android Platform Tools ou adiciona adb ao PATH."
}

$adb = Resolve-Adb
Write-Host "VazaoSovereignTrader — emparelhamento inicial por USB" -ForegroundColor Cyan
Write-Host "1. Liga o Android por USB e desbloqueia o ecrã."
Write-Host "2. Autoriza a mensagem de depuração USB no Android, se aparecer."
& $adb start-server | Out-Host
$devices = @(& $adb devices | Select-Object -Skip 1 | Where-Object { $_ -match "\S+\s+device$" })
$unauthorized = @(& $adb devices | Select-Object -Skip 1 | Where-Object { $_ -match "\S+\s+unauthorized$" })

if ($devices.Count -eq 0) {
    if ($unauthorized.Count -gt 0) {
        throw "Android detetado mas não autorizado. Desbloqueia o telemóvel, aceita a chave RSA de depuração USB e executa novamente."
    }
    throw "Nenhum Android autorizado encontrado. Confirma o cabo USB, ativa Opções de programador/Depuração USB e executa novamente."
}
if ($devices.Count -ne 1) {
    throw "Foram encontrados $($devices.Count) dispositivos autorizados. Liga apenas um Android para evitar emparelhar o dispositivo errado."
}

if ($ApkPath) {
    if (-not (Test-Path $ApkPath -PathType Leaf)) { throw "APK não encontrado: $ApkPath" }
    & $adb install -r $ApkPath
    if ($LASTEXITCODE -ne 0) { throw "A instalação do APK falhou (código $LASTEXITCODE)." }
    Write-Host "APK instalado. A abertura inicial continua a ser feita pelo utilizador." -ForegroundColor Green
}

& $adb reverse tcp:8765 tcp:8765
if ($LASTEXITCODE -ne 0) { throw "Não foi possível criar o túnel USB para a porta 8765." }

Write-Host ""
Write-Host "Túnel USB ativo: no Android, o PC fica temporariamente disponível em http://127.0.0.1:8765" -ForegroundColor Green
Write-Host "No APK, usa esse endereço e introduz o token local do PC manualmente."
Write-Host "O túnel só funciona enquanto o USB/ADB estiver ligado e autorizado."
Write-Host "Para uso na mesma Wi-Fi ou fora de casa, configura depois a rede local ou Tailscale conforme docs/ANDROID_FIRST_PAIRING.md."
Write-Host "Este assistente não lê nem imprime tokens, não desativa proteções Android e não ativa REAL."
