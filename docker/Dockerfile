# AI-Trader 高频交易系统 Dockerfile
# 基于 Python 3.11，支持富途 OpenD 连接

FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libffi-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt requirements-hft.txt ./

# 安装 Python 依赖
RUN pip install --upgrade pip && \
    pip install -r requirements.txt && \
    pip install -r requirements-hft.txt

# 复制项目代码
COPY . .

# 创建数据目录
RUN mkdir -p /app/data/agent_data /app/logs

# 暴露端口
# 9090: Prometheus 指标
# 8010: Futu Trade MCP 服务
EXPOSE 9090 8010

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:9090/health || exit 1

# 默认命令
CMD ["python", "main_hft.py", "--dry-run"]
