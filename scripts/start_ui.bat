@echo off
REM Start AI-Trader Web UI

setlocal enabledelayedexpansion

echo ============================================
echo   AI-Trader Web UI Server
echo ============================================
echo.

REM 设置工作目录
cd /d %~dp0..
set PROJECT_ROOT=%cd%

echo Project root: %PROJECT_ROOT%
echo.

echo Starting Web UI server...
echo.
echo ========================================
echo   Web UI: http://localhost:8888
echo   Press Ctrl+C to stop the server
echo ========================================
echo.

cd /d "%PROJECT_ROOT%\docs"
python -m http.server 8888

echo.
echo [OK] Web server stopped

endlocal
pause
