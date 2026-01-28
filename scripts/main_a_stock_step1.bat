@echo off
REM A-Share - Step 1: Prepare Data

setlocal enabledelayedexpansion

echo ============================================
echo   AI-Trader A-Share - Data Preparation
echo ============================================
echo.

REM 设置工作目录
cd /d %~dp0..
set PROJECT_ROOT=%cd%

echo Project root: %PROJECT_ROOT%
echo.

echo Preparing A-Share data...
cd /d "%PROJECT_ROOT%\data\A_stock"

REM for alphavantage
if exist get_daily_price_alphavantage.py (
    echo Running get_daily_price_alphavantage.py...
    python get_daily_price_alphavantage.py
    if errorlevel 1 echo [WARN] get_daily_price_alphavantage.py encountered errors
)

if exist merge_jsonl_alphavantage.py (
    echo Running merge_jsonl_alphavantage.py...
    python merge_jsonl_alphavantage.py
    if errorlevel 1 echo [WARN] merge_jsonl_alphavantage.py encountered errors
)

REM for tushare (uncomment if using tushare)
REM python get_daily_price_tushare.py
REM python merge_jsonl_tushare.py

echo.
echo [OK] A-Share data preparation completed!

endlocal
pause
