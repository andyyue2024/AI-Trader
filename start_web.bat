@echo off
REM AI-Trader Web UI 启动脚本 (Windows)
REM 启动 FastAPI 仪表盘服务

echo ============================================
echo   AI-Trader Web Dashboard
echo ============================================
echo.

REM 检查 Python
python --version > nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python 3.10+
    pause
    exit /b 1
)

REM 设置工作目录
cd /d %~dp0

REM 检查依赖
echo [1/3] Checking dependencies...
pip show fastapi > nul 2>&1
if errorlevel 1 (
    echo [INFO] Installing FastAPI...
    pip install fastapi uvicorn websockets
)

REM 设置环境变量
set PYTHONPATH=%cd%

REM 启动 Web UI
echo [2/3] Starting Web Dashboard...
echo.
echo   Dashboard URL: http://localhost:8888
echo   Press Ctrl+C to stop
echo.

python -c "from web.dashboard import run_dashboard; run_dashboard(host='0.0.0.0', port=8888)"

pause
