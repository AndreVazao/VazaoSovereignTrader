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
New-Item -ItemType Directory -Force -Path $build, (Join-Path $build "config"), (Join-Path $build "docs") | Out-Null

& $python -m pip install --upgrade pip
& $python -m pip install -r requirements-pc.txt
& $python -m pip install pyinstaller

$env:PLAYWRIGHT_BROWSERS_PATH = "0"
& $python -m playwright install chromium
if ($LASTEXITCODE -ne 0) { throw "Playwright Chromium installation failed." }
$env:PLAYWRIGHT_BROWSERS_PATH = "0"


& $python -m PyInstaller --noconfirm --clean --onefile --noconsole --name VazaoSovereignTrader --paths . --collect-all playwright PC_ENGINE/main.py
if ($LASTEXITCODE -ne 0) { throw "PC engine EXE build failed." }

& $python -m PyInstaller --noconfirm --clean --onefile --console --name VazaoSovereignTrader-MarketData --paths . PC_ENGINE/tools/run_market_data_collector.py
if ($LASTEXITCODE -ne 0) { throw "Market-data collector EXE build failed." }

Copy-Item (Join-Path $dist "VazaoSovereignTrader.exe") $build
Copy-Item (Join-Path $dist "VazaoSovereignTrader-MarketData.exe") $build
Copy-Item "PC_ENGINE\config\config.example.json" (Join-Path $build "config\config.example.json")
Copy-Item "README.md" (Join-Path $build "README.md")
Copy-Item "docs\WINDOWS_ONE_CLICK_INSTALL.md" (Join-Path $build "docs\WINDOWS_ONE_CLICK_INSTALL.md")

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

& $iscc $iss
if ($LASTEXITCODE -ne 0) { throw "Inno Setup compilation failed." }

Write-Host "Windows installer created in installer\installer-output." -ForegroundColor Green
