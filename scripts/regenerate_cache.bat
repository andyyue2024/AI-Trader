@echo off
REM Regenerate Frontend Cache
REM Run this script after updating trading data to regenerate the pre-computed cache files

setlocal enabledelayedexpansion

echo ========================================
echo   Regenerating Frontend Cache
echo ========================================
echo.

REM 设置工作目录
cd /d %~dp0..
set PROJECT_ROOT=%cd%

echo Project root: %PROJECT_ROOT%
echo.

REM 检查 Python 和 PyYAML
python -c "import yaml" 2>nul
if errorlevel 1 (
    echo [ERROR] Python with PyYAML not found.
    echo Please install: pip install pyyaml
    pause
    exit /b 1
)

echo Using Python: python
echo.

REM 检查脚本文件
if not exist "%PROJECT_ROOT%\scripts\precompute_frontend_cache.py" (
    echo [ERROR] precompute_frontend_cache.py not found!
    pause
    exit /b 1
)

echo Running cache generation script...
python "%PROJECT_ROOT%\scripts\precompute_frontend_cache.py"

if errorlevel 1 (
    echo [ERROR] Cache generation failed!
    pause
    exit /b 1
)

echo.
echo ========================================
echo   Cache regeneration complete!
echo ========================================
echo.
echo Generated files:
echo   - docs/data/us_cache.json
echo   - docs/data/cn_cache.json
echo.
echo These files will be automatically used by the frontend for faster loading.
echo Commit these files to your repository for GitHub Pages deployment.

endlocal
pause
