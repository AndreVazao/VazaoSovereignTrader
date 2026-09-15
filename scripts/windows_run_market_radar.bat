@echo off
setlocal
cd /d %~dp0..
if not exist PC_ENGINE\.venv\Scripts\python.exe (
  echo [ERRO] Ambiente virtual nao encontrado.
  echo Execute scripts\windows_setup.bat primeiro.
  exit /b 1
)
PC_ENGINE\.venv\Scripts\python.exe PC_ENGINE\tools\run_market_radar.py
