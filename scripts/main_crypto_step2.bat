@echo off
REM Cryptocurrency - Step 2: Start MCP Services

setlocal enabledelayedexpansion

echo ============================================
echo   AI-Trader Crypto - MCP Services
echo ============================================
echo.

REM 设置工作目录
cd /d %~dp0..
set PROJECT_ROOT=%cd%

echo Project root: %PROJECT_ROOT%
echo.

echo Starting MCP services...
cd /d "%PROJECT_ROOT%\agent_tools"

if exist start_mcp_services.py (
    python start_mcp_services.py
) else (
    echo [ERROR] start_mcp_services.py not found!
    pause
    exit /b 1
)

echo.
echo [OK] MCP services started!

endlocal
pause
