#!/bin/bash
# AI-Trader Web UI 启动脚本 (Linux/Mac)
# 启动 FastAPI 仪表盘服务

echo "============================================"
echo "  AI-Trader Web Dashboard"
echo "============================================"
echo ""

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python3 not found. Please install Python 3.10+"
    exit 1
fi

# 设置工作目录
cd "$(dirname "$0")"

# 检查依赖
echo "[1/3] Checking dependencies..."
if ! python3 -c "import fastapi" 2>/dev/null; then
    echo "[INFO] Installing FastAPI..."
    pip3 install fastapi uvicorn websockets
fi

# 设置环境变量
export PYTHONPATH=$(pwd)

# 启动 Web UI
echo "[2/3] Starting Web Dashboard..."
echo ""
echo "  Dashboard URL: http://localhost:8888"
echo "  Press Ctrl+C to stop"
echo ""

python3 -c "from web.dashboard import run_dashboard; run_dashboard(host='0.0.0.0', port=8888)"
