@echo off
setlocal
cd /d "%~dp0.."

set "PYTHONW="
if exist "PC_ENGINE\.venv\Scripts\pythonw.exe" set "PYTHONW=PC_ENGINE\.venv\Scripts\pythonw.exe"
if not defined PYTHONW if exist ".venv\Scripts\pythonw.exe" set "PYTHONW=.venv\Scripts\pythonw.exe"

if not defined PYTHONW (
  echo Ambiente Python nao encontrado.
  echo Execute scripts\windows_setup.bat primeiro.
  pause
  exit /b 1
)

start "" "%PYTHONW%" "PC_ENGINE\main.py"
timeout /t 5 /nobreak >nul
start "" "http://127.0.0.1:8765/dashboard"
exit /b 0
