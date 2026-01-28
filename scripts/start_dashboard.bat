@echo off
REM AI-Trader Web Dashboard (FastAPI) Startup Script

setlocal enabledelayedexpansion

echo ============================================
echo   AI-Trader Web Dashboard
echo ============================================
echo.

REM 设置工作目录
cd /d %~dp0..
set PROJECT_ROOT=%cd%

echo Project root: %PROJECT_ROOT%
echo.

REM 检查 FastAPI 依赖
python -c "import fastapi" 2>nul
if errorlevel 1 (
    echo [INFO] Installing FastAPI dependencies...
    pip install fastapi uvicorn websockets
)

echo ========================================
echo   Dashboard URL: http://localhost:8888
echo   Press Ctrl+C to stop the server
echo ========================================
echo.

python -c "from web.dashboard import run_dashboard; run_dashboard(host='0.0.0.0', port=8888)"

echo.
echo [OK] Dashboard stopped

endlocal
pause
