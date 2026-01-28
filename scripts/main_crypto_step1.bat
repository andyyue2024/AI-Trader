@echo off
REM Cryptocurrency - Step 1: Prepare Data

setlocal enabledelayedexpansion

echo ============================================
echo   AI-Trader Crypto - Data Preparation
echo ============================================
echo.

REM 设置工作目录
cd /d %~dp0..
set PROJECT_ROOT=%cd%

echo Project root: %PROJECT_ROOT%
echo.

REM 确保目录存在
if not exist "%PROJECT_ROOT%\data\crypto" (
    echo Creating data\crypto directory...
    mkdir "%PROJECT_ROOT%\data\crypto"
)

echo Preparing cryptocurrency data...
cd /d "%PROJECT_ROOT%\data\crypto"

echo Current directory: %cd%

if exist get_daily_price_crypto.py (
    echo Running: python get_daily_price_crypto.py
    python get_daily_price_crypto.py
    if errorlevel 1 echo [WARN] get_daily_price_crypto.py encountered errors
) else (
    echo [SKIP] get_daily_price_crypto.py not found
)

if exist merge_crypto_jsonl.py (
    echo Running: python merge_crypto_jsonl.py
    python merge_crypto_jsonl.py
    if errorlevel 1 echo [WARN] merge_crypto_jsonl.py encountered errors
) else (
    echo [SKIP] merge_crypto_jsonl.py not found
)

echo.
echo [OK] Crypto data preparation completed!

endlocal
pause
