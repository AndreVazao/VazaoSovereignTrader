@echo off
setlocal
cd /d "%~dp0.."

if not exist "PC_ENGINE\.venv\Scripts\python.exe" (
  echo Runtime nao instalado. A executar setup...
  call "scripts\windows_setup.bat"
  if errorlevel 1 exit /b 1
)

if not exist "PC_ENGINE\config\config.local.json" (
  echo Configuracao nao encontrada. A executar setup...
  call "scripts\windows_setup.bat"
  if errorlevel 1 exit /b 1
)

set "PYTHONW=PC_ENGINE\.venv\Scripts\pythonw.exe"
if not exist "%PYTHONW%" set "PYTHONW=PC_ENGINE\.venv\Scripts\python.exe"

echo A iniciar VazaoSovereignTrader em PAPER...
start "" "%PYTHONW%" "PC_ENGINE\main.py"

timeout /t 5 /nobreak >nul
start "" "http://127.0.0.1:8765/dashboard"
exit /b 0
