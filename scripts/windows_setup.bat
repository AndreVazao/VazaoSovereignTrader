@echo off
setlocal
cd /d "%~dp0.."
python -m venv PC_ENGINE\.venv
call PC_ENGINE\.venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements-pc.txt
if not exist PC_ENGINE\config\config.local.json copy PC_ENGINE\config\config.example.json PC_ENGINE\config\config.local.json
echo.
echo Setup concluido. Agora corre scripts\windows_run_pc_engine.bat
pause
