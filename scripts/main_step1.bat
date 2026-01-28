@echo off
REM US Stock - Step 1: Prepare Data

setlocal enabledelayedexpansion

echo ============================================
echo   AI-Trader US Stock - Data Preparation
echo ============================================
echo.

REM 设置工作目录
cd /d %~dp0..
set PROJECT_ROOT=%cd%

echo Project root: %PROJECT_ROOT%
echo.

echo Preparing US stock data...
cd /d "%PROJECT_ROOT%\data"

REM 检查文件是否存在并运行
if exist get_interdaily_price.py (
    echo Running get_interdaily_price.py...
    python get_interdaily_price.py
    if errorlevel 1 echo [WARN] get_interdaily_price.py encountered errors
) else (
    echo [SKIP] get_interdaily_price.py not found
)

if exist merge_jsonl.py (
    echo Running merge_jsonl.py...
    python merge_jsonl.py
    if errorlevel 1 echo [WARN] merge_jsonl.py encountered errors
) else (
    echo [SKIP] merge_jsonl.py not found
)

echo.
echo [OK] Data preparation completed!

endlocal
pause
