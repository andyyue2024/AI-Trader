#!/bin/bash
# AI-Trader 高频交易系统启动脚本 (Linux/Mac)

set -e

echo "========================================"
echo "  AI-Trader High Frequency Trading"
echo "========================================"
echo

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python3 is not installed"
    exit 1
fi

# 默认参数
SYMBOLS="TQQQ QQQ"
DRY_RUN="--dry-run"
CONFIG=""

# 解析参数
while [[ $# -gt 0 ]]; do
    case $1 in
        --symbols)
            SYMBOLS="$2"
            shift 2
            ;;
        --live)
            DRY_RUN=""
            shift
            ;;
        --config)
            CONFIG="--config $2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --symbols \"SYM1 SYM2\"  Trading symbols (default: TQQQ QQQ)"
            echo "  --live                 Run in live trading mode (default: dry-run)"
            echo "  --config FILE          Use custom config file"
            echo "  --help                 Show this help"
            exit 0
            ;;
        *)
            shift
            ;;
    esac
done

echo "[INFO] Starting AI-Trader HFT System"
echo "  Symbols: $SYMBOLS"
if [ -z "$DRY_RUN" ]; then
    echo "  Mode: LIVE TRADING"
    echo ""
    echo "[WARNING] Running in LIVE trading mode!"
    read -p "Are you sure? (yes/no): " CONFIRM
    if [ "$CONFIRM" != "yes" ]; then
        echo "Aborted."
        exit 0
    fi
else
    echo "  Mode: Dry Run (Simulation)"
fi
echo

# 切换到脚本目录
cd "$(dirname "$0")"

# 运行
python3 main_hft.py --symbols $SYMBOLS $DRY_RUN $CONFIG
