# AI-Trader 高频交易系统

## 概述

基于富途 OpenD 的高频交易系统，实现以下目标：
- **下单延迟**: ≤ 0.0014s (1.4ms)
- **全流程延迟**: 1分钟行情 → 模型决策 → 下单 ≤ 1s
- **滑点控制**: ≤ 0.2%
- **日成交额**: ≥ 5万美金
- **成交率**: ≥ 95%
- **夏普比率**: ≥ 2
- **最大回撤**: ≤ 15%
- **日内熔断**: 3% 自动触发

## 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                    AI-Trader HFT System                     │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │  行情订阅   │  │  AI 决策    │  │  交易执行   │         │
│  │  (1min K)   │──│  (模型)     │──│  (OpenD)    │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
│         │                │                │                 │
│         ▼                ▼                ▼                 │
│  ┌─────────────────────────────────────────────────┐       │
│  │                风控模块                          │       │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐        │       │
│  │  │ 熔断器   │ │ 回撤监控 │ │ 滑点检查 │        │       │
│  │  └──────────┘ └──────────┘ └──────────┘        │       │
│  └─────────────────────────────────────────────────┘       │
│         │                                                   │
│         ▼                                                   │
│  ┌─────────────────────────────────────────────────┐       │
│  │                监控告警                          │       │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐        │       │
│  │  │Prometheus│ │ Grafana  │ │ 飞书告警 │        │       │
│  │  └──────────┘ └──────────┘ └──────────┘        │       │
│  └─────────────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────────────┘
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
pip install -r requirements-hft.txt
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件，填入必要的配置
```

### 3. 启动 OpenD

确保富途 OpenD 已经启动并运行在 `127.0.0.1:11111`。

### 4. 运行（模拟模式）

```bash
python main_hft.py --symbols TQQQ QQQ --dry-run
```

### 5. Docker 部署

```bash
cd docker
./start.sh up
```

## 核心模块

### 富途交易模块 (`futu/`)

- **opend_client.py**: OpenD 连接管理，支持连接池和自动重连
- **trade_executor.py**: 交易执行器，实现 long/short/flat 操作
- **quote_subscriber.py**: 实时行情订阅，支持盘前/盘后交易

```python
from futu.trade_executor import FutuTradeExecutor

executor = FutuTradeExecutor(trd_env=1)  # 模拟环境

# 做多
result = await executor.long("TQQQ", 100)

# 做空
result = await executor.short("TQQQ", 100)

# 平仓
result = await executor.flat("TQQQ")
```

### 风控模块 (`risk_control/`)

- **circuit_breaker.py**: 熔断器，日内 3% 亏损自动触发
- **drawdown_monitor.py**: 回撤监控，最大 15% 限制
- **slippage_checker.py**: 滑点检查，超过 0.2% 告警
- **risk_manager.py**: 综合风险管理器

```python
from risk_control.risk_manager import RiskManager

rm = RiskManager()
rm.initialize(50000.0)  # 初始资金

# 交易前检查
check = rm.pre_trade_check("TQQQ", "long", 100, 75.0)
if check.allowed:
    # 执行交易
    pass

# 交易后检查
rm.post_trade_check("TQQQ", 75.0, 75.05)
```

### 监控模块 (`monitoring/`)

- **metrics_exporter.py**: Prometheus 指标导出
- **feishu_alert.py**: 飞书告警，异常 5 分钟内通知
- **grafana_dashboard.py**: Grafana 仪表盘配置

```python
from monitoring.metrics_exporter import start_metrics_server
from monitoring.feishu_alert import send_feishu_alert

# 启动指标服务
exporter = start_metrics_server(port=9090)

# 发送告警
send_feishu_alert(
    title="风控告警",
    content="回撤超过 10%",
    level=AlertLevel.WARNING
)
```

## 配置说明

### configs/hft_config.json

```json
{
  "trading": {
    "initial_cash": 50000.0,      // 初始资金
    "max_position_per_symbol": 0.20,  // 单标的最大仓位
    "trading_interval": 60        // 交易间隔(秒)
  },
  "risk": {
    "daily_loss_limit": 0.03,     // 日内亏损限制
    "max_drawdown": 0.15,         // 最大回撤
    "max_slippage": 0.002         // 最大滑点
  },
  "futu": {
    "host": "127.0.0.1",
    "port": 11111,
    "trd_env": 1                  // 0=真实, 1=模拟
  }
}
```

## 测试

### 运行所有测试

```bash
python run_tests.py
```

### 运行快速测试

```bash
python run_tests.py --quick
```

### 运行覆盖率测试

```bash
python run_tests.py --coverage
```

测试覆盖率目标: ≥ 80%

## Docker 部署

### 服务说明

| 服务 | 端口 | 说明 |
|------|------|------|
| ai-trader | 9090, 8010 | 高频交易主服务 |
| prometheus | 9091 | 指标收集 |
| grafana | 3000 | 可视化仪表盘 |

### 启动

```bash
cd docker
./start.sh up
```

### 查看日志

```bash
./start.sh logs
```

### 停止

```bash
./start.sh down
```

## 扩展到其他标的

系统设计支持零改动部署到其他美股标的：

```bash
# SPXL/SOXL
python main_hft.py --symbols SPXL SOXL

# 科技股
python main_hft.py --symbols AAPL MSFT GOOGL

# 自定义配置
python main_hft.py --config configs/custom_config.json
```

## 性能优化

1. **连接池**: OpenD 连接池默认 3 个连接
2. **异步执行**: 所有 IO 操作使用 asyncio
3. **缓存**: 行情数据 10 秒缓存
4. **批量处理**: 支持多标的并行处理

## 注意事项

1. **OpenD 需要单独运行**: 在 Windows/Mac 上运行 OpenD 客户端
2. **模拟账户**: 建议先在模拟环境测试
3. **行情订阅**: 实时行情可能需要付费订阅
4. **交易时段**: 支持盘前(04:00-09:30)和盘后(16:00-20:00)交易

## 许可证

MIT License
