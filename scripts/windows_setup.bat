@echo off
setlocal
cd /d "%~dp0.."

echo.
echo ==========================================
echo   VazaoSovereignTrader - Windows Setup
echo ==========================================
echo.

where py >nul 2>&1
if %errorlevel%==0 (
  set "PY=py -3"
) else (
  where python >nul 2>&1
  if not %errorlevel%==0 (
    echo Python 3.11+ nao encontrado.
    echo Instale Python 3.11+ e marque "Add Python to PATH".
    pause
    exit /b 1
  )
  set "PY=python"
)

if not exist "PC_ENGINE\.venv\Scripts\python.exe" (
  echo [1/6] A criar ambiente Python...
  %PY% -m venv PC_ENGINE\.venv
  if errorlevel 1 goto :fail
)

set "PYTHON=PC_ENGINE\.venv\Scripts\python.exe"

echo [2/6] A instalar dependencias...
"%PYTHON%" -m pip install --upgrade pip
if errorlevel 1 goto :fail
"%PYTHON%" -m pip install -r requirements-pc.txt
if errorlevel 1 goto :fail

echo [3/6] A instalar Chromium/Playwright...
"%PYTHON%" -m playwright install chromium
if errorlevel 1 goto :fail

echo [4/6] A preparar configuracao e dados...
if not exist "PC_ENGINE\config\config.local.json" copy /Y "PC_ENGINE\config\config.example.json" "PC_ENGINE\config\config.local.json" >nul
if not exist "PC_ENGINE\data\radar" mkdir "PC_ENGINE\data\radar"
if not exist "PC_ENGINE\data\browser\profiles" mkdir "PC_ENGINE\data\browser\profiles"
if not exist "PC_ENGINE\data\logs" mkdir "PC_ENGINE\data\logs"

echo [5/6] A verificar runtime...
"%PYTHON%" -m compileall -q PC_ENGINE
if errorlevel 1 goto :fail
"%PYTHON%" -c "import flask,ccxt,pydantic,requests,websocket,playwright; print('Dependencias: OK')"
if errorlevel 1 goto :fail

echo [6/6] A garantir token local...
powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\ensure_windows_token.ps1"
if errorlevel 1 goto :fail

echo.
echo SETUP CONCLUIDO.
echo.
echo Agora podes executar:
echo   scripts\windows_run_pc_engine.bat
echo.
echo Para instalar arranque automatico 24/7:
echo   scripts\install_windows_autostart.ps1
echo.
echo O modo inicial e PAPER e a recolha publica nao exige API keys.
echo.
pause
exit /b 0

:fail
echo.
echo SETUP FALHOU. Verifica a mensagem acima.
pause
exit /b 1
