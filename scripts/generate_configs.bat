@echo off
REM 生成所有预定义 HFT 配置文件

setlocal enabledelayedexpansion

echo ============================================
echo   Generate HFT Configuration Files
echo ============================================
echo.

cd /d %~dp0..
set PROJECT_ROOT=%cd%

echo Project root: %PROJECT_ROOT%
echo.

python -c "from configs.config_manager import generate_all_configs; generate_all_configs('./configs')"

echo.
echo [OK] Configuration files generated!
echo.
echo Generated files:
dir /b configs\hft_*.json 2>nul

endlocal
pause
