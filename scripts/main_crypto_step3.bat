@echo off
REM Cryptocurrency - Step 3: Start Trading Agent

setlocal enabledelayedexpansion

echo ============================================
echo   AI-Trader Crypto - Trading Agent
echo ============================================
echo.

REM 设置工作目录
cd /d %~dp0..
set PROJECT_ROOT=%cd%

echo Project root: %PROJECT_ROOT%
echo.

echo Starting the cryptocurrency trading agent...
echo.

set CONFIG_FILE=configs/default_crypto_config.json
if not exist "%CONFIG_FILE%" (
    echo [ERROR] %CONFIG_FILE% not found!
    pause
    exit /b 1
)

echo Using config: %CONFIG_FILE%
python main.py %CONFIG_FILE%

echo.
echo [OK] AI-Trader stopped

endlocal
pause
