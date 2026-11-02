[CmdletBinding()]
param(
    [string]$InstallRoot = (Join-Path $env:LOCALAPPDATA "VazaoSovereignTrader"),
    [string]$OutputRoot = (Join-Path $env:USERPROFILE "Documents\VST-Local-Validation"),
    [int]$Port = 8765
)
$ErrorActionPreference = "Stop"
$startedAt = Get-Date
$stamp = $startedAt.ToUniversalTime().ToString("yyyyMMddTHHmmssZ")
$reportDir = Join-Path $OutputRoot $stamp
New-Item -ItemType Directory -Force -Path $reportDir | Out-Null
$checks = [System.Collections.Generic.List[object]]::new()

function Add-Check {
    param([string]$Name, [string]$Status, [string]$Detail)
    $checks.Add([pscustomobject]@{ name = $Name; status = $Status; detail = $Detail })
}
function Get-SafeConfigSummary {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { return @{ found = $false; error = "config_missing" } }
    try {
        $cfg = Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json
        return @{
            found = $true
            mode = [string]$cfg.mode
            server_host = [string]$cfg.server.host
            server_port = $cfg.server.port
            auto_start_paper = [bool]$cfg.engine.auto_start_paper
            real_flags = @{
                allow_real = if ($null -ne $cfg.autonomous_execution -and $null -ne $cfg.autonomous_execution.PSObject.Properties["allow_real"]) { [bool]$cfg.autonomous_execution.allow_real } else { $null }
                auto_promote_real = if ($null -ne $cfg.autonomous_execution -and $null -ne $cfg.autonomous_execution.PSObject.Properties["auto_promote_real"]) { [bool]$cfg.autonomous_execution.auto_promote_real } else { $null }
                fast_path_allow_real = if ($null -ne $cfg.fast_path -and $null -ne $cfg.fast_path.PSObject.Properties["allow_real"]) { [bool]$cfg.fast_path.allow_real } else { $null }
            }
            credentials_values_read_or_reported = $false
        }
    } catch { return @{ found = $true; error = "config_parse_failed:$($_.Exception.GetType().Name)" } }
}
function Get-JsonFileSummary {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { return @{ exists = $false } }
    try {
        $value = Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json
        return @{
            exists = $true
            valid_json = $true
            status = [string]$value.status
            timestamp = $value.timestamp
            critical_checks = @($value.critical_checks)
            paper_only = $value.paper_only
            real_promotion_attempted = $value.real_promotion_attempted
        }
    } catch { return @{ exists = $true; valid_json = $false; error = $_.Exception.GetType().Name } }
}

$configPath = Join-Path $InstallRoot "config\config.local.json"
if (-not (Test-Path -LiteralPath $configPath -PathType Leaf)) { $configPath = Join-Path $InstallRoot "config\config.example.json" }
$configSummary = Get-SafeConfigSummary -Path $configPath
if ($configSummary.found -and -not $configSummary.error) {
    if ($configSummary.mode -eq "PAPER") { Add-Check "config_mode" "PASS" "Configured mode is PAPER." }
    else { Add-Check "config_mode" "FAIL" "Configured mode is not PAPER; no trading action was attempted." }
    if ($configSummary.server_host -in @("127.0.0.1", "localhost", "::1")) {
        Add-Check "api_binding" "PASS" "API is configured for loopback."
    } else { Add-Check "api_binding" "CHECK" "API host is not loopback. Verify approved private binding; do not expose publicly." }
    $realFlags = @($configSummary.real_flags.allow_real, $configSummary.real_flags.auto_promote_real, $configSummary.real_flags.fast_path_allow_real)
    if ($realFlags -contains $true) {
        Add-Check "real_execution_flags" "FAIL" "At least one known REAL execution flag is enabled. Do not operate the engine."
    } elseif ($realFlags -contains $null) {
        Add-Check "real_execution_flags" "FAIL" "One or more REAL execution flags are missing or unverifiable. Do not operate the engine."
    } else { Add-Check "real_execution_flags" "PASS" "Known REAL execution flags are explicitly disabled." }
} else { Add-Check "config" "FAIL" "Config missing or invalid; no configuration values were printed." }

$enginePath = Join-Path $InstallRoot "VazaoSovereignTrader.exe"
if (Test-Path -LiteralPath $enginePath -PathType Leaf) {
    $engineItem = Get-Item -LiteralPath $enginePath
    $engineSummary = @{ exists = $true; sha256 = (Get-FileHash -LiteralPath $enginePath -Algorithm SHA256).Hash; length_bytes = $engineItem.Length; last_write_utc = $engineItem.LastWriteTimeUtc.ToString("o") }
    Add-Check "installed_executable" "PASS" "Executable exists; SHA-256 recorded."
} else {
    $engineSummary = @{ exists = $false }
    Add-Check "installed_executable" "FAIL" "Expected executable was not found under InstallRoot."
}

$healthUrl = "http://127.0.0.1:$Port/health"
try {
    $healthResponse = Invoke-RestMethod -Uri $healthUrl -Method Get -TimeoutSec 3
    $healthSummary = @{
        reachable = $true
        service = [string]$healthResponse.service
        mode = [string]$healthResponse.mode
        engine_status = [string]$healthResponse.engine_status
        engine_running = [bool]$healthResponse.engine_running
        readiness_note = [string]$healthResponse.readiness_note
    }
    if ($healthSummary.service -eq "VazaoSovereignTrader" -and $healthSummary.mode -eq "PAPER") {
        Add-Check "api_liveness" "PASS" "Loopback health endpoint responded in PAPER mode."
    } else { Add-Check "api_liveness" "FAIL" "Health endpoint responded but service identity or mode failed the PAPER contract." }
    if ($healthSummary.engine_running) { Add-Check "engine_liveness" "PASS" "Engine reports RUNNING; this is not proof of trading readiness." }
    else { Add-Check "engine_liveness" "CHECK" "API is reachable but engine does not report RUNNING." }
} catch {
    $healthSummary = @{ reachable = $false; error = $_.Exception.GetType().Name; url = $healthUrl }
    Add-Check "api_liveness" "NOT RUN" "Loopback health endpoint did not respond. Script did not start or stop services."
}

$startupPath = Join-Path $InstallRoot "data\owners"
$startupSummary = @{ found = $false; candidates = @() }
if (Test-Path -LiteralPath $startupPath -PathType Container) {
    $reports = @(Get-ChildItem -LiteralPath $startupPath -Filter "startup_health.json" -File -Recurse -ErrorAction SilentlyContinue)
    foreach ($reportFile in $reports) {
        $summary = Get-JsonFileSummary -Path $reportFile.FullName
        $startupSummary.candidates += @{ relative_path = $reportFile.FullName.Substring($InstallRoot.Length).TrimStart("\"); summary = $summary }
    }
    $startupSummary.found = $reports.Count -gt 0
}
if ($startupSummary.found) {
    $bad = @($startupSummary.candidates | Where-Object {
        $_.summary.valid_json -ne $true -or $_.summary.status -ne "READY" -or $_.summary.paper_only -ne $true -or $_.summary.real_promotion_attempted -ne $false -or @($_.summary.critical_checks).Count -gt 0
    })
    if ($bad.Count -eq 0) { Add-Check "startup_health" "PASS" "Owner-scoped reports are valid and READY/PAPER with no critical checks." }
    else { Add-Check "startup_health" "FAIL" "At least one owner-scoped startup report is invalid or not READY/PAPER." }
} else { Add-Check "startup_health" "NOT RUN" "No owner-scoped startup_health.json found; no report was fabricated." }

$vaultRoot = Join-Path $InstallRoot "vault"
$vaultSummary = @{ path_relative = "vault"; exists = (Test-Path -LiteralPath $vaultRoot -PathType Container); directories = @{}; files = @{} }
foreach ($name in @("learning", "backups", "imports", "exports", "logs")) {
    $dir = Join-Path $vaultRoot $name
    $vaultSummary.directories[$name] = Test-Path -LiteralPath $dir -PathType Container
    $vaultSummary.files[$name] = if (Test-Path -LiteralPath $dir -PathType Container) { @(Get-ChildItem -LiteralPath $dir -File -Recurse -ErrorAction SilentlyContinue).Count } else { 0 }
}
if ($vaultSummary.exists) { Add-Check "vault_presence" "PASS" "Vault directory exists; only directory names and file counts were recorded." }
else { Add-Check "vault_presence" "CHECK" "Vault directory not found. Audit does not create or migrate vault data." }

$taskSummary = @{}
foreach ($taskName in @("VazaoSovereignTrader", "VazaoSovereignTrader-MarketData")) {
    try {
        $task = Get-ScheduledTask -TaskName $taskName -ErrorAction Stop
        $taskSummary[$taskName] = @{ exists = $true; state = [string]$task.State }
    } catch { $taskSummary[$taskName] = @{ exists = $false; state = "NOT_FOUND" } }
}
Add-Check "scheduled_tasks_inventory" "PASS" "Scheduled-task presence/state inventoried; no task was changed."

$report = [ordered]@{
    schema_version = 1
    report_type = "VST_LOCAL_BACKEND_READ_ONLY_AUDIT"
    created_utc = $startedAt.ToUniversalTime().ToString("o")
    host = @{ os = [System.Environment]::OSVersion.VersionString; powershell = $PSVersionTable.PSVersion.ToString(); computer_name_redacted = $true }
    install_root = $InstallRoot
    checks = @($checks)
    config_summary = $configSummary
    executable = $engineSummary
    api_health = $healthSummary
    startup_health = $startupSummary
    vault_inventory = $vaultSummary
    scheduled_tasks = $taskSummary
    safety = @{ read_only = $true; started_or_stopped_processes = $false; changed_config = $false; read_or_reported_credentials = $false; real_orders_submitted = $false; public_network_requests = $false }
}
$jsonPath = Join-Path $reportDir "runtime-audit.json"
$mdPath = Join-Path $reportDir "runtime-audit.md"
$report | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $jsonPath -Encoding utf8
$lines = [System.Collections.Generic.List[string]]::new()
$lines.Add("# VST Local Backend Read-only Audit")
$lines.Add("")
$lines.Add("- Created UTC: $($report.created_utc)")
$lines.Add("- Install root: $InstallRoot")
$lines.Add("- Result folder: $reportDir")
$lines.Add("")
$lines.Add("| Check | Status | Detail |")
$lines.Add("|---|---|---|")
foreach ($check in $checks) {
    $detail = ([string]$check.detail).Replace("|", "\|").Replace([string][char]13, " ").Replace([string][char]10, " ")
    $lines.Add("| $($check.name) | $($check.status) | $detail |")
}
$lines.Add("")
$lines.Add("## Safety")
$lines.Add("")
$lines.Add("- Read-only audit: yes")
$lines.Add("- Services/processes started or stopped: no")
$lines.Add("- Configuration changed: no")
$lines.Add("- Credentials values collected: no")
$lines.Add("- REAL orders submitted: no")
$lines.Add("- Public network requests: no")
$lines.Add("")
$lines.Add("## Interpretation")
$lines.Add("")
$lines.Add("A reachable /health endpoint proves API liveness only. It does not prove learning quality, market-data freshness, recovery correctness, or authorization to trade.")
$lines | Set-Content -LiteralPath $mdPath -Encoding utf8
Write-Output "VST local backend audit written:"
Write-Output $mdPath
Write-Output $jsonPath
Write-Output "No services were started/stopped; no configuration was changed."
exit 0
