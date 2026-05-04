@echo off
setlocal
cd /d "%~dp0.."
call PC_ENGINE\.venv\Scripts\activate.bat
python PC_ENGINE\main.py
pause
