@echo off
setlocal
cd /d "%~dp0.."
if not exist "PC_ENGINE\.venv\Scripts\python.exe" (
  echo Trader not installed. Run scripts\setup_windows.ps1 first.
  exit /b 1
)
"PC_ENGINE\.venv\Scripts\python.exe" "PC_ENGINE\tools\run_market_data_collector.py"
