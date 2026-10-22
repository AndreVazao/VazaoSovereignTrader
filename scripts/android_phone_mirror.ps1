# Open a manually controlled mirror of the physical Android phone.
# This is an interactive GUI session, not a headless background service.
# It never taps the screen, submits forms, reads app data, or enters credentials.

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("open")]
    [string]$Action,

    [string]$DeviceSerial
)

$ErrorActionPreference = "Stop"

function Resolve-Adb {
    $command = Get-Command adb -ErrorAction SilentlyContinue
    if ($command) { return $command.Source }

    $candidates = @(
        (Join-Path $env:LOCALAPPDATA "Android\Sdk\platform-tools\adb.exe"),
        (Join-Path $env:ProgramFiles "Android\platform-tools\adb.exe")
    ) | Where-Object { $_ -and (Test-Path $_ -PathType Leaf) }

    if ($candidates.Count -gt 0) { return $candidates[0] }
    throw "ADB não encontrado. Instala Android Platform Tools e autoriza o telemóvel manualmente."
}

function Resolve-Scrcpy {
    $command = Get-Command scrcpy -ErrorAction SilentlyContinue
    if ($command) { return $command.Source }

    $candidates = @(
        (Join-Path $env:LOCALAPPDATA "Programs\scrcpy\scrcpy.exe"),
        (Join-Path $env:ProgramFiles "scrcpy\scrcpy.exe")
    ) | Where-Object { $_ -and (Test-Path $_ -PathType Leaf) }

    if ($candidates.Count -gt 0) { return $candidates[0] }
    throw "scrcpy não encontrado. Instala scrcpy a partir da sua distribuição oficial; este script não descarrega software."
}

$adb = Resolve-Adb
$scrcpy = Resolve-Scrcpy
$output = @(& $adb devices 2>&1)
if ($LASTEXITCODE -ne 0) {
    throw "ADB não conseguiu listar dispositivos. Confirma o cabo USB e o serviço ADB."
}

$headerIndex = -1
for ($i = 0; $i -lt $output.Count; $i++) {
    if ("$($output[$i])".Trim().StartsWith("List of devices attached")) {
        $headerIndex = $i
        break
    }
}
if ($headerIndex -lt 0) {
    throw "Resposta ADB inválida; não foi iniciada nenhuma sessão."
}

$devices = @()
$unauthorized = @()
$offline = @()
for ($i = $headerIndex + 1; $i -lt $output.Count; $i++) {
    $line = "$($output[$i])".Trim()
    if (-not $line) { continue }
    $parts = $line -split "\s+"
    if ($parts.Count -lt 2) { continue }
    if ($parts[1] -eq "device") { $devices += $parts[0] }
    elseif ($parts[1] -eq "unauthorized") { $unauthorized += $parts[0] }
    elseif ($parts[1] -eq "offline") { $offline += $parts[0] }
}

if ($DeviceSerial) {
    if ($devices -notcontains $DeviceSerial) {
        if ($unauthorized -contains $DeviceSerial) {
            throw "O dispositivo indicado ainda não foi autorizado no ecrã Android."
        }
        if ($offline -contains $DeviceSerial) {
            throw "O dispositivo indicado está offline."
        }
        throw "O serial indicado não corresponde a um dispositivo ADB autorizado."
    }
    $selectedSerial = $DeviceSerial
}
else {
    if ($devices.Count -ne 1) {
        throw "Encontrados $($devices.Count) dispositivos autorizados. Indica -DeviceSerial para escolher exatamente um."
    }
    $selectedSerial = $devices[0]
}

# Low-bandwidth defaults. The operator controls the physical phone manually.
$process = Start-Process -FilePath $scrcpy -ArgumentList @(
    "--serial", $selectedSerial,
    "--max-size=1280",
    "--video-bit-rate=4M",
    "--max-fps=30",
    "--no-audio",
    "--window-title=VST Android Operator"
) -PassThru

Write-Output "SCREEN_SESSION_STARTED: serial redacted; PID $($process.Id)"
Write-Output "Fecha a janela scrcpy quando terminares. A sessão não é iniciada automaticamente com o Windows."
Write-Output "Login, MFA e todas as ações nas exchanges permanecem manuais. Não uses esta sessão para automatizar ordens."
