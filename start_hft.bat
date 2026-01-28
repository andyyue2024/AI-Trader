@echo off
REM AI-Trader 高频交易系统启动脚本 (Windows)

echo ========================================
echo   AI-Trader High Frequency Trading
echo ========================================
echo.

REM 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH
    exit /b 1
)

REM 设置默认参数
set SYMBOLS=TQQQ QQQ
set DRY_RUN=--dry-run
set CONFIG=

REM 解析参数
:parse_args
if "%~1"=="" goto run
if "%~1"=="--symbols" (
    set SYMBOLS=%~2
    shift
    shift
    goto parse_args
)
if "%~1"=="--live" (
    set DRY_RUN=
    shift
    goto parse_args
)
if "%~1"=="--config" (
    set CONFIG=--config %~2
    shift
    shift
    goto parse_args
)
if "%~1"=="--help" (
    goto show_help
)
shift
goto parse_args

:show_help
echo Usage: start_hft.bat [options]
echo.
echo Options:
echo   --symbols "SYM1 SYM2"  Trading symbols (default: TQQQ QQQ)
echo   --live                 Run in live trading mode (default: dry-run)
echo   --config FILE          Use custom config file
echo   --help                 Show this help
echo.
exit /b 0

:run
echo [INFO] Starting AI-Trader HFT System
echo   Symbols: %SYMBOLS%
echo   Mode: %DRY_RUN%
if "%DRY_RUN%"=="" (
    echo   [WARNING] Running in LIVE trading mode!
    echo.
    set /p CONFIRM="Are you sure? (yes/no): "
    if not "%CONFIRM%"=="yes" (
        echo Aborted.
        exit /b 0
    )
)
echo.

REM 切换到项目目录
cd /d %~dp0

REM 运行
python main_hft.py --symbols %SYMBOLS% %DRY_RUN% %CONFIG%
