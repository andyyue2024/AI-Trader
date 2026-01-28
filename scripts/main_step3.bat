@echo off
REM US Stock - Step 3: Start Trading Agent

setlocal enabledelayedexpansion

echo ============================================
echo   AI-Trader US Stock - Trading Agent
echo ============================================
echo.

REM 设置工作目录
cd /d %~dp0..
set PROJECT_ROOT=%cd%

echo Project root: %PROJECT_ROOT%
echo.

echo Starting the main trading agent...
echo.

REM 检查配置文件
set CONFIG_FILE=configs/default_hour_config.json
if not exist "%CONFIG_FILE%" (
    echo [WARN] %CONFIG_FILE% not found, trying default_config.json
    set CONFIG_FILE=configs/default_config.json
)

if not exist "%CONFIG_FILE%" (
    echo [ERROR] No config file found!
    pause
    exit /b 1
)

echo Using config: %CONFIG_FILE%
python main.py %CONFIG_FILE%

echo.
echo [OK] AI-Trader stopped

endlocal
pause
