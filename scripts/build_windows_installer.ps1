param(
    [string]$AppVersion = "2026.10.1"
)

$ErrorActionPreference = "Stop"

$repo = Split-Path -Parent $PSScriptRoot
Set-Location $repo

$python = "python"
$build = Join-Path $repo "installer\build"
$dist = Join-Path $repo "dist"

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw "Python 3.11+ is required by the CI build image."
}

if (Test-Path $build) { Remove-Item $build -Recurse -Force }
New-Item -ItemType Directory -Force -Path $build, (Join-Path $build "config"), (Join-Path $build "docs"), (Join-Path $build "scripts") | Out-Null

& $python -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw "pip upgrade failed." }
& $python -m pip install -r requirements-pc.txt
if ($LASTEXITCODE -ne 0) { throw "PC runtime dependency installation failed." }
& $python -m pip install pyinstaller
if ($LASTEXITCODE -ne 0) { throw "PyInstaller installation failed." }

$browserBundle = Join-Path $build "ms-playwright"
if (Test-Path $browserBundle) { Remove-Item $browserBundle -Recurse -Force }
New-Item -ItemType Directory -Force -Path $browserBundle | Out-Null
$env:PLAYWRIGHT_BROWSERS_PATH = $browserBundle
& $python -m playwright install chromium --no-shell
if ($LASTEXITCODE -ne 0) { throw "Playwright Chromium installation failed." }

& $python -m PyInstaller --noconfirm --clean --onefile --noconsole --name VazaoSovereignTrader --paths . --collect-all playwright PC_ENGINE/main.py
if ($LASTEXITCODE -ne 0) { throw "PC engine EXE build failed." }

$workerBuilds = @(
    @{ Name = "VazaoSovereignTrader-MarketData"; Entry = "PC_ENGINE/tools/run_market_data_collector.py"; Console = $true },
    @{ Name = "VazaoSovereignTrader-Radar"; Entry = "PC_ENGINE/tools/run_market_radar.py"; Console = $false },
    @{ Name = "VazaoSovereignTrader-TopOfBook"; Entry = "PC_ENGINE/tools/run_top_of_book_collector.py"; Console = $false },
    @{ Name = "VazaoSovereignTrader-L2"; Entry = "PC_ENGINE/tools/run_l2_market_data_collector.py"; Console = $false },
    @{ Name = "VazaoSovereignTrader-MarketDataService"; Entry = "PC_ENGINE/services/public_market_data_service.py"; Console = $false }
)
foreach ($worker in $workerBuilds) {
    $consoleFlag = if ($worker.Console) { "--console" } else { "--noconsole" }
    & $python -m PyInstaller --noconfirm --clean --onefile $consoleFlag --name $worker.Name --paths . $worker.Entry
    if ($LASTEXITCODE -ne 0) { throw "Worker EXE build failed: $($worker.Name)" }
    Copy-Item (Join-Path $dist ($worker.Name + ".exe")) $build
}

Copy-Item (Join-Path $dist "VazaoSovereignTrader.exe") $build
Copy-Item "PC_ENGINE\config\config.example.json" (Join-Path $build "config\config.example.json")
Copy-Item "README.md" (Join-Path $build "README.md")
Copy-Item "docs\WINDOWS_ONE_CLICK_INSTALL.md" (Join-Path $build "docs\WINDOWS_ONE_CLICK_INSTALL.md")
Copy-Item "docs\PUBLIC_MARKET_DATA_SERVICE.md" (Join-Path $build "docs\PUBLIC_MARKET_DATA_SERVICE.md")
Copy-Item "scripts\ensure_windows_token.ps1" (Join-Path $build "scripts\ensure_windows_token.ps1")
Copy-Item "scripts\stop_market_data_service.ps1" (Join-Path $build "scripts\stop_market_data_service.ps1")

$iss = Join-Path $repo "installer\VazaoSovereignTrader.iss"
$iscc = $null
$command = Get-Command ISCC.exe -ErrorAction SilentlyContinue
if ($command) {
    $iscc = $command.Source
}
if (-not $iscc) {
    foreach ($candidate in @(
        "$env:ProgramFiles(x86)\Inno Setup 7\ISCC.exe",
        "$env:ProgramFiles\Inno Setup 7\ISCC.exe",
        "$env:ProgramFiles(x86)\Inno Setup 6\ISCC.exe",
        "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
    )) {
        if ($candidate -and (Test-Path $candidate)) { $iscc = $candidate; break }
    }
}
if (-not $iscc) {
    $roots = @($env:ProgramFiles, ${env:ProgramFiles(x86)})
    foreach ($root in $roots) {
        if (-not $root) { continue }
        $found = Get-ChildItem -Path $root -Filter ISCC.exe -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($found) { $iscc = $found.FullName; break }
    }
}
if (-not $iscc) { throw "Inno Setup ISCC.exe not found." }

& $iscc $iss "/DAppVersion=$AppVersion" "/O$repo\installer-output"
if ($LASTEXITCODE -ne 0) { throw "Inno Setup compilation failed." }
$output = Join-Path $repo "installer-output"
New-Item -ItemType Directory -Force -Path $output | Out-Null
$installerName = "VazaoSovereignTrader-Setup.exe"
$expected = Join-Path $output $installerName
$generated = Get-ChildItem -Path $output -Filter "VazaoSovereignTrader-Setup*.exe" -File -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1
if (-not $generated) { throw "Inno Setup completed but no setup EXE was found." }
if ($generated.FullName -ne $expected) {
    Copy-Item $generated.FullName $expected -Force
}
if (-not (Test-Path $expected)) { throw "Installer normalization failed: $expected" }

Write-Host "Windows installer created in installer\installer-output." -ForegroundColor Green
