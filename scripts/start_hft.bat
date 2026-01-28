@echo off
REM AI-Trader High Frequency Trading System Startup Script

setlocal enabledelayedexpansion

echo ============================================
echo   AI-Trader HFT System
echo ============================================
echo.

REM 设置工作目录
cd /d %~dp0..
set PROJECT_ROOT=%cd%

echo Project root: %PROJECT_ROOT%
echo.

REM 检查 main_hft.py 是否存在
if not exist "%PROJECT_ROOT%\main_hft.py" (
    echo [ERROR] main_hft.py not found!
    pause
    exit /b 1
)

REM 设置默认参数
set SYMBOLS=TQQQ,QQQ
set DRY_RUN=--dry-run

echo ========================================
echo   Configuration:
echo     Symbols: %SYMBOLS%
echo     Mode: Dry Run (Simulation)
echo ========================================
echo.

echo Starting HFT System...
echo Press Ctrl+C to stop
echo.

python "%PROJECT_ROOT%\main_hft.py" --symbols %SYMBOLS% %DRY_RUN%

echo.
echo [OK] HFT System stopped

endlocal
pause
