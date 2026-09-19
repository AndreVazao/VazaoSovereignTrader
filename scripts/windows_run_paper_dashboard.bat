@echo off
setlocal
cd /d "%~dp0.."

if exist ".venv\Scripts\pythonw.exe" (
  start "" ".venv\Scripts\pythonw.exe" "PC_ENGINE\main.py"
) else (
  echo Ambiente Python nao encontrado em .venv.
  echo Execute windows_setup.bat primeiro.
  pause
  exit /b 1
)

timeout /t 4 /nobreak >nul
start "" "http://127.0.0.1:8765/dashboard"
exit /b 0
