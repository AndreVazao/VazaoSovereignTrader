# Android Emulator lifecycle helper — optional, on-demand, headless.
# This script does not install SDK components, create AVDs, configure accounts,
# enable ADB over TCP, or start automatically with Windows.

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("list", "start", "status", "stop")]
    [string]$Action,

    [string]$AvdName,

    [switch]$ConfirmStop
)

$ErrorActionPreference = "Stop"

function Resolve-AndroidSdk {
    $candidates = @(
        $env:ANDROID_SDK_ROOT,
        $env:ANDROID_HOME,
        (Join-Path $env:LOCALAPPDATA "Android\Sdk")
    ) | Where-Object { $_ } | Select-Object -Unique

    foreach ($candidate in $candidates) {
        $emulator = Join-Path $candidate "emulator\emulator.exe"
        if (Test-Path $emulator -PathType Leaf) {
            return [pscustomobject]@{
                Root = $candidate
                Emulator = $emulator
            }
        }
    }

    throw "Android Emulator não encontrado. Instala-o pelo Android SDK Manager ou define ANDROID_SDK_ROOT. O script não instala componentes."
}

function Get-AvdNames([string]$EmulatorPath) {
    $output = @(& $EmulatorPath -list-avds 2>&1)
    if ($LASTEXITCODE -ne 0) {
        throw "Não foi possível listar AVDs. Confirma a instalação do Android Emulator."
    }

    return @($output | ForEach-Object { "$_".Trim() } | Where-Object { $_ })
}

function Get-AvdProcesses([string]$Name) {
    $escaped = [regex]::Escape($Name)
    $pattern = "(?i)(?:^|\s)-avd\s+`"$escaped`"(?:\s|$)|(?:^|\s)-avd\s+$escaped(?:\s|$)"

    try {
        return @(Get-CimInstance Win32_Process -Filter "Name = 'emulator.exe'" |
            Where-Object { $_.CommandLine -and $_.CommandLine -match $pattern })
    }
    catch {
        throw "Não foi possível inspecionar os processos do emulador: $($_.Exception.GetType().Name)"
    }
}

$sdk = Resolve-AndroidSdk
$avds = Get-AvdNames -EmulatorPath $sdk.Emulator

if ($Action -eq "list") {
    if ($avds.Count -eq 0) {
        Write-Output "Nenhum AVD configurado. Cria um manualmente no Android Studio; este script não cria dispositivos."
    }
    else {
        $avds | ForEach-Object { Write-Output $_ }
    }
    exit 0
}

if ([string]::IsNullOrWhiteSpace($AvdName)) {
    throw "Indica -AvdName com o nome exato de um AVD. Usa -Action list para ver os nomes."
}

if ($avds -notcontains $AvdName) {
    throw "AVD '$AvdName' não existe nesta instalação. Usa -Action list; nenhum dispositivo foi iniciado."
}

$running = @(Get-AvdProcesses -Name $AvdName)

switch ($Action) {
    "status" {
        if ($running.Count -eq 0) {
            Write-Output "STOPPED: $AvdName"
        }
        else {
            Write-Output "RUNNING: $AvdName (PID(s): $($running.ProcessId -join ', '))"
        }
    }

    "start" {
        if ($running.Count -gt 0) {
            Write-Output "ALREADY_RUNNING: $AvdName (PID(s): $($running.ProcessId -join ', '))"
            exit 0
        }

        # No window/audio/boot animation. This still consumes CPU/RAM while running.
        $process = Start-Process -FilePath $sdk.Emulator -ArgumentList @(
            "-avd", $AvdName,
            "-no-window",
            "-no-audio",
            "-no-boot-anim",
            "-gpu", "auto"
        ) -PassThru

        Write-Output "START_REQUESTED: $AvdName (PID: $($process.Id))"
        Write-Output "The emulator boots asynchronously. Check status with ADB before using it."
    }

    "stop" {
        if (-not $ConfirmStop) {
            throw "Para parar '$AvdName', repete com -ConfirmStop. Nenhum processo foi terminado."
        }
        if ($running.Count -eq 0) {
            Write-Output "ALREADY_STOPPED: $AvdName"
            exit 0
        }

        foreach ($processInfo in $running) {
            Stop-Process -Id $processInfo.ProcessId -Force
        }
        Write-Output "STOP_REQUESTED: $AvdName"
    }
}
