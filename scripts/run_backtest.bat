@echo off
REM 运行回测

setlocal enabledelayedexpansion

echo ============================================
echo   AI-Trader Backtest
echo ============================================
echo.

cd /d %~dp0..
set PROJECT_ROOT=%cd%

echo Project root: %PROJECT_ROOT%
echo.

REM 默认参数
set SYMBOLS=AAPL,MSFT
set START_DATE=2024-01-01
set END_DATE=2024-12-31

echo Configuration:
echo   Symbols: %SYMBOLS%
echo   Period: %START_DATE% to %END_DATE%
echo.

python -c "from backtest import run_backtest; result = run_backtest(symbols='%SYMBOLS%'.split(','), start_date='%START_DATE%', end_date='%END_DATE%'); result.print_summary()"

echo.
echo [OK] Backtest completed!

endlocal
pause
