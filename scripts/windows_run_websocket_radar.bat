@echo off
setlocal
cd /d "%~dp0.."
if not exist ".venv\Scripts\python.exe" (
  echo Ambiente virtual nao encontrado.
  echo Execute scripts\windows_setup.bat primeiro.
  exit /b 1
)
.venv\Scripts\python.exe -m PC_ENGINE.tools.run_websocket_radar --symbols BTC/USDT,ETH/USDT --exchanges binance,coinbase,okx
endlocal
