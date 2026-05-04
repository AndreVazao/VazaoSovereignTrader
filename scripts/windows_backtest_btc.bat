@echo off
setlocal
cd /d "%~dp0.."
call PC_ENGINE\.venv\Scripts\activate.bat
python PC_ENGINE\tools\run_backtest.py --exchange binance --symbol BTC/USDT --limit 500
pause
