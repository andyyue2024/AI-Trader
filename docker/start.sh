#!/bin/bash
# AI-Trader Docker 启动脚本

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  AI-Trader High Frequency Trading     ${NC}"
echo -e "${GREEN}========================================${NC}"

# 检查 Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed${NC}"
    exit 1
fi

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo -e "${RED}Error: Docker Compose is not installed${NC}"
    exit 1
fi

# 检查环境变量
if [ -z "$OPENAI_API_KEY" ]; then
    echo -e "${YELLOW}Warning: OPENAI_API_KEY not set${NC}"
fi

# 创建必要目录
mkdir -p ../data ../logs

# 默认参数
MODE=${1:-"up"}
DRY_RUN=${DRY_RUN:-"true"}
SYMBOLS=${SYMBOLS:-"TQQQ QQQ"}

case $MODE in
    "up")
        echo -e "${GREEN}Starting AI-Trader...${NC}"
        echo -e "  Mode: ${DRY_RUN == 'true' && echo 'Dry Run' || echo 'Live Trading'}"
        echo -e "  Symbols: $SYMBOLS"
        docker compose up -d
        echo -e "${GREEN}Services started!${NC}"
        echo -e "  - AI-Trader: http://localhost:9090/health"
        echo -e "  - Prometheus: http://localhost:9091"
        echo -e "  - Grafana: http://localhost:3000 (admin/admin123)"
        ;;
    "down")
        echo -e "${YELLOW}Stopping AI-Trader...${NC}"
        docker compose down
        echo -e "${GREEN}Services stopped${NC}"
        ;;
    "logs")
        docker compose logs -f ai-trader
        ;;
    "restart")
        echo -e "${YELLOW}Restarting AI-Trader...${NC}"
        docker compose restart ai-trader
        ;;
    "build")
        echo -e "${GREEN}Building AI-Trader image...${NC}"
        docker compose build --no-cache
        ;;
    "status")
        docker compose ps
        ;;
    *)
        echo "Usage: $0 {up|down|logs|restart|build|status}"
        exit 1
        ;;
esac
