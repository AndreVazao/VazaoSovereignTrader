param(
    [Parameter(Mandatory = $true)]
    [string]$InstalledAppDir,
    [Parameter(Mandatory = $true)]
    [string]$PythonExe,
    [string]$TestRoot = (Join-Path $env:RUNNER_TEMP "VST-Installed-Supervisor-Lifecycle")
)

$ErrorActionPreference = "Stop"
$InstalledAppDir = (Resolve-Path -LiteralPath $InstalledAppDir).Path
$supervisorSource = Join-Path $InstalledAppDir "VazaoSovereignTrader-MarketDataService.exe"
if (-not (Test-Path -LiteralPath $supervisorSource)) {
    throw "Installed market-data supervisor executable is missing."
}
if (-not (Test-Path -LiteralPath $PythonExe)) {
    $pythonCommand = Get-Command $PythonExe -ErrorAction Stop
    $PythonExe = $pythonCommand.Source
}

if (Test-Path -LiteralPath $TestRoot) {
    Remove-Item -LiteralPath $TestRoot -Recurse -Force
}
$appDir = Join-Path $TestRoot "app"
$dataDir = Join-Path $TestRoot "data"
$buildDir = Join-Path $TestRoot "fake-worker-build"
$distDir = Join-Path $TestRoot "fake-worker-dist"
New-Item -ItemType Directory -Force -Path $appDir, $dataDir, $buildDir, $distDir | Out-Null
Copy-Item -LiteralPath $supervisorSource -Destination (Join-Path $appDir "VazaoSovereignTrader-MarketDataService.exe")

$fixture = Join-Path (Split-Path -Parent $PSScriptRoot) "tests\fixtures\fake_market_data_worker.py"
if (-not (Test-Path -LiteralPath $fixture)) {
    throw "Deterministic fake worker fixture is missing."
}
& $PythonExe -m PyInstaller --noconfirm --clean --onefile --console --name VSTFakeMarketDataWorker --distpath $distDir --workpath $buildDir --specpath $buildDir $fixture
if ($LASTEXITCODE -ne 0) {
    throw "Could not build deterministic fake worker executable."
}
$fakeWorker = Join-Path $distDir "VSTFakeMarketDataWorker.exe"
if (-not (Test-Path -LiteralPath $fakeWorker)) {
    throw "Deterministic fake worker executable was not produced."
}
$workerNames = @(
    "VazaoSovereignTrader-MarketData.exe",
    "VazaoSovereignTrader-Radar.exe",
    "VazaoSovereignTrader-TopOfBook.exe",
    "VazaoSovereignTrader-L2.exe"
)
foreach ($name in $workerNames) {
    Copy-Item -LiteralPath $fakeWorker -Destination (Join-Path $appDir $name)
}

$supervisor = Join-Path $appDir "VazaoSovereignTrader-MarketDataService.exe"
$healthPath = Join-Path $dataDir "market_data_service_health.json"
$stdoutPath = Join-Path $TestRoot "supervisor.stdout.log"
$stderrPath = Join-Path $TestRoot "supervisor.stderr.log"
$controlPath = Join-Path $dataDir "stop.request"

function Get-ServiceHealth {
    if (-not (Test-Path -LiteralPath $healthPath)) { return $null }
    try {
        return (Get-Content -LiteralPath $healthPath -Raw | ConvertFrom-Json)
    } catch {
        return $null
    }
}

function Wait-ServiceStatus {
    param(
        [string[]]$Statuses,
        [int]$TimeoutSeconds,
        [System.Diagnostics.Process]$Process,
        [string]$Label
    )
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        $health = Get-ServiceHealth
        if ($health -and $Statuses -contains [string]$health.status) {
            return $health
        }
        $Process.Refresh()
        if ($Process.HasExited) {
            $stdout = if (Test-Path $stdoutPath) { Get-Content -LiteralPath $stdoutPath -Raw } else { "" }
            $stderr = if (Test-Path $stderrPath) { Get-Content -LiteralPath $stderrPath -Raw } else { "" }
            $serviceLog = Join-Path $dataDir "logs\market_data_service.log"
            $log = if (Test-Path $serviceLog) { Get-Content -LiteralPath $serviceLog -Tail 40 | Out-String } else { "" }
            throw "${Label}: supervisor exited early with code $($Process.ExitCode). stdout=$stdout stderr=$stderr service_log=$log"
        }
        Start-Sleep -Milliseconds 250
    }
    $last = Get-ServiceHealth
    $lastStatus = if ($last) { $last.status } else { "missing" }
    $healthDetail = if ($last) { $last | ConvertTo-Json -Depth 12 -Compress } else { "missing" }
    $serviceLog = Join-Path $dataDir "logs\market_data_service.log"
    $logTail = if (Test-Path -LiteralPath $serviceLog) { Get-Content -LiteralPath $serviceLog -Tail 80 | Out-String } else { "missing" }
    throw ($Label + ": timed out waiting for " + ($Statuses -join '/') + " (last=" + $lastStatus + ") health=" + $healthDetail + " service_log=" + $logTail)
}

function Start-TestSupervisor {
    param(
        [double]$IgnoreStopSeconds = 0,
        [switch]$PreserveStopRequest
    )
    # A normal start clears a stale request. A lock-contender test must not
    # mutate the active supervisor's control channel while it owns the lock.
    if (-not $PreserveStopRequest -and (Test-Path -LiteralPath $controlPath)) {
        Remove-Item -LiteralPath $controlPath -Force
    }
    [Environment]::SetEnvironmentVariable(
        "VST_FAKE_WORKER_IGNORE_STOP_SECONDS",
        [string]$IgnoreStopSeconds,
        "Process"
    )
    $arguments = '--app-dir "{0}" --data-dir "{1}" --symbols BTC/USDT ETH/USDT --health-interval-seconds 1' -f $appDir, $dataDir
    try {
        $process = Start-Process -FilePath $supervisor -ArgumentList $arguments -PassThru -WindowStyle Hidden -RedirectStandardOutput $stdoutPath -RedirectStandardError $stderrPath
    } finally {
        [Environment]::SetEnvironmentVariable("VST_FAKE_WORKER_IGNORE_STOP_SECONDS", $null, "Process")
    }
    return $process
}

function Request-TestStop {
    Set-Content -LiteralPath $controlPath -Value "stop" -NoNewline -Encoding ascii
}

function Confirm-Stopped {
    param([System.Diagnostics.Process]$Process, [string]$Label)
    $health = Wait-ServiceStatus -Statuses @("STOPPED") -TimeoutSeconds 35 -Process $Process -Label $Label
    $Process.WaitForExit(5000) | Out-Null
    $Process.Refresh()
    if (-not $Process.HasExited) {
        throw "${Label}: STOPPED health was published but supervisor process remains alive."
    }
    if ($Process.ExitCode -ne 0) {
        throw "${Label}: supervisor exited with code $($Process.ExitCode)."
    }
    foreach ($worker in $health.workers.PSObject.Properties) {
        if ($worker.Value.running) {
            throw "${Label}: worker '$($worker.Name)' remained marked as running after STOPPED."
        }
    }
}

$process = $null
try {
    # Exercise installed supervisor executable with four deterministic worker
    # processes; no exchange endpoints, credentials or trading APIs are used.
    $process = Start-TestSupervisor
    $health = Wait-ServiceStatus -Statuses @("RUNNING") -TimeoutSeconds 30 -Process $process -Label "initial start"
    if (-not $health.all_workers_running -or -not $health.all_worker_heartbeats_fresh) {
        throw "Initial RUNNING status did not include four live workers with fresh heartbeats."
    }
    Request-TestStop
    Confirm-Stopped -Process $process -Label "initial stop"

    # Reacquiring the same data-directory lock proves the first instance
    # released ownership and that the installed supervisor can restart.
    $process = Start-TestSupervisor
    $health = Wait-ServiceStatus -Statuses @("RUNNING") -TimeoutSeconds 30 -Process $process -Label "restart"
    Request-TestStop
    Confirm-Stopped -Process $process -Label "restart stop"

    # Workers deliberately ignore the first stop request. The supervisor must
    # publish DEGRADED, retain ownership, and later reach STOPPED after they
    # exit cooperatively; it must never claim a false successful shutdown.
    $process = Start-TestSupervisor -IgnoreStopSeconds 20
    $health = Wait-ServiceStatus -Statuses @("RUNNING") -TimeoutSeconds 30 -Process $process -Label "delayed-stop start"
    Request-TestStop
    $degraded = Wait-ServiceStatus -Statuses @("DEGRADED") -TimeoutSeconds 18 -Process $process -Label "cooperative timeout"
    if ($degraded.shutdown_reason -ne "worker_shutdown_timeout") {
        throw "Delayed workers did not expose worker_shutdown_timeout."
    }

    # The still-live first supervisor must retain the singleton lock. A
    # competing supervisor must fail before it can create duplicate workers.
    $contender = Start-TestSupervisor -PreserveStopRequest
    if (-not $contender.WaitForExit(5000)) {
        Request-TestStop
        $contender.WaitForExit(35000) | Out-Null
        throw "A second supervisor started while the previous workers were still alive."
    }
    $contender.Refresh()
    if ($contender.ExitCode -eq 0) {
        throw "A competing supervisor unexpectedly acquired the active singleton lock."
    }

    Confirm-Stopped -Process $process -Label "cooperative recovery"

    Write-Host "Installed supervisor lifecycle passed: start -> RUNNING -> STOPPED -> restart -> DEGRADED on slow workers -> cooperative recovery -> STOPPED. No exchange access or trading actions were used."
} finally {
    [Environment]::SetEnvironmentVariable("VST_FAKE_WORKER_IGNORE_STOP_SECONDS", $null, "Process")
    if ($process) {
        $process.Refresh()
        if (-not $process.HasExited) {
            try {
                Request-TestStop
                if (-not $process.WaitForExit(35000)) {
                    Write-Warning "Supervisor did not exit during cleanup; process was not force-killed."
                }
            } catch {
                Write-Warning "Cooperative cleanup request failed: $($_.Exception.Message)"
            }
        }
    }
}
