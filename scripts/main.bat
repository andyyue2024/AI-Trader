@echo off
REM AI-Trader 主启动脚本
REM 用于启动完整的交易环境

setlocal enabledelayedexpansion

echo ============================================
echo   AI-Trader Main Startup Script
echo ============================================
echo.

REM 设置工作目录为脚本所在目录的父目录
cd /d %~dp0..
set PROJECT_ROOT=%cd%

echo Project root: %PROJECT_ROOT%
echo.

echo [1/4] Getting and merging price data...
cd /d "%PROJECT_ROOT%\data"
if exist get_daily_price.py (
    python get_daily_price.py
    if errorlevel 1 echo [WARN] get_daily_price.py failed, continuing...
)
if exist merge_jsonl.py (
    python merge_jsonl.py
    if errorlevel 1 echo [WARN] merge_jsonl.py failed, continuing...
)

echo [2/4] Starting MCP services...
cd /d "%PROJECT_ROOT%\agent_tools"
start "MCP Services" /B python start_mcp_services.py

REM 等待 MCP 服务启动
echo Waiting for MCP services to start...
timeout /t 3 /nobreak > nul

echo [3/4] Starting the main trading agent...
cd /d "%PROJECT_ROOT%"
python main.py configs/default_config.json

echo.
echo [OK] AI-Trader stopped

echo [4/4] Starting web server...
cd /d "%PROJECT_ROOT%\docs"
echo Web server will start at http://localhost:8888
echo Press Ctrl+C to stop
python -m http.server 8888

echo [OK] Web server stopped

endlocal
pause
