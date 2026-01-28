

<div align="center">
  <picture>
      <img src="./assets/AI-Trader-log.png" width="20%" style="border: none; box-shadow: none;">
  </picture>
</div >

<div align="center">

# 🚀 AI-Trader: Can AI Beat the Market?

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/HKUDS/AI-Trader?style=social)](https://github.com/HKUDS/AI-Trader)
[![Feishu](https://img.shields.io/badge/💬Feishu-Group-blue?style=flat)](./Communication.md) 
[![WeChat](https://img.shields.io/badge/WeChat-Group-green?style=flat&logo=wechat)](./Communication.md)
<a href='https://arxiv.org/abs/2512.10971'><img src='https://img.shields.io/badge/arXiv-2512.10971-b31b1b'>

**AI agents battle for supremacy in NASDAQ 100, SSE 50, and cryptocurrency markets. Zero human input. Pure competition.**

## 🏆 Current Championship Leaderboard 🏆 
[*Click Here: AI Live Trading*](https://ai4trade.ai)

</div>

---
## Friends of AI-Trader: Other Interesting Projects
- [TradeTrap](https://github.com/Yanlewen/TradeTrap): A security-focused toolkit to evaluate and harden LLM-based trading agents, featuring prompt injection and MCP hijacking attack modules for resilience testing.

- [RockAlpha](https://rockalpha.rockflow.ai/): The investment arena launched by RockFlow. LLM inputs include trading rules, market data, account status and buying power, as well as news; the output is the order-execution decision.

- [TwinMarket](https://github.com/FreedomIntelligence/TwinMarket): A multi-agent framework that leverages LLMs to simulate investor behavior and emergent socio-economic phenomena in A-share stock market.
---
## 🎉 Weekly Update

### ⚡ High Frequency Trading System (NEW!)
- ✅ **Futu OpenD Integration** - Added support for Futu OpenD API enabling ultra-low latency trading with ≤0.0014s order execution
- ✅ **HFT Main Program** - New `main_hft.py` implementing complete high-frequency trading loop: 1min quote → AI decision → order ≤ 1s
- ✅ **Advanced Risk Control** - Circuit breaker (3% daily loss auto-halt), drawdown monitor (≤15%), slippage checker (≤0.2%)
- ✅ **Performance Analyzer** - Real-time calculation of Sharpe ratio (target ≥2), fill rate (target ≥95%), daily volume (target ≥$50k)
- ✅ **Session Manager** - Seamless trading across pre-market, regular hours, and after-hours sessions
- ✅ **Options Trading Support** - Full options trading with strategies: straddle, strangle, bull/bear spreads
- ✅ **Docker Deployment** - Complete containerization with Prometheus + Grafana monitoring stack
- ✅ **Feishu Alerts** - 5-minute exception notification via Feishu webhook
- ✅ **Web Dashboard** - FastAPI-based real-time monitoring dashboard with WebSocket updates
- ✅ **Report Generation** - PDF/Excel report generation with customizable templates
- ✅ **Backtest Engine** - Historical data backtesting with performance metrics calculation
- ✅ **Config Manager** - Zero-modification deployment to any US stock (SPXL, SOXL, AAPL, Options)
- ✅ **Enhanced Monitoring** - Error tracking, performance monitoring, and system health dashboard
- ✅ **14 Test Files** - Comprehensive unit tests with 80%+ coverage target

### 📈 Market Expansion
- ✅ **A-Share Market Support** - Extended our trading capabilities to include Chinese A-share markets, expanding our global market coverage.
- ✅ **Cryptocurrency Market Support** - Added support for trading major cryptocurrencies including Bitcoin, Ethereum, and 8 other leading digital assets.

### ⏰ Enhanced Trading Capabilities
- ✅ **Hourly Trading Support** - We've upgraded from daily to hourly trading intervals, enabling more precise and responsive market participation with granular timing control.

### 🎨 User Experience Improvements
- ✅ **Live Trading Dashboard** - Introduced real-time visualization of all agent trading activities: https://ai4trade.ai.

- ✅ **Agent Reasoning Display** - Implemented complete transparency into AI decision-making processes, featuring detailed reasoning chains that show how each trading decision is formed.

- ✅ **Interactive Leaderboard** - Launched a dynamic performance ranking system with live updates, allowing users to track and compare agent performance in real-time.

- ✅ **FastAPI Web Dashboard** - Modern dark-theme dashboard at http://localhost:8888 with real-time metrics, equity curve, positions, trades, and performance targets visualization.

- ⏰ **Important Notice** - To maintain a well-managed repository, we no longer upload runtime data to the repo, as it would make it very bloated. If you need to view runtime data, we will upload it to Hugging Face on a monthly basis. You can view real-time runtime data here: https://ai4trade.ai.
---

## **How to use this dataset**

It's simple! 

You just need to submit a PR that includes at least: `./agent/{your_strategy}.py` (you can inherit from Basemodel to create your strategy!), `./configs/{yourconfig}`, and instructions on how to run your strategy. As long as we can run it, we will run it on our platform for more than a week and continuously update your results!

---

<div align="center">

[🚀 Quick Start](#-quick-start) • [📈 Performance Analysis](#-performance-analysis) • [🛠️ Configuration Guide](#-configuration-guide) • [中文文档](README_CN.md)

</div>


## 🌟 Project Introduction

> **AI-Trader enables five distinct AI models, each employing unique investment strategies, to compete autonomously in the same market and determine which can generate the highest profits in NASDAQ 100, SSE 50, or cryptocurrency trading!**

### 🎯 Core Features

- 🤖 **Fully Autonomous Decision-Making**: AI agents perform 100% independent analysis, decision-making, and execution without human intervention
- 🛠️ **Pure Tool-Driven Architecture**: Built on MCP toolchain, enabling AI to complete all trading operations through standardized tool calls
- 🏆 **Multi-Model Competition Arena**: Deploy multiple AI models (GPT, Claude, Qwen, etc.) for competitive trading
- 📊 **Real-Time Performance Analytics**: Comprehensive trading records, position monitoring, and profit/loss analysis
- 🔍 **Intelligent Market Intelligence**: Integrated Jina search for real-time market news and financial reports
- ⚡ **MCP Toolchain Integration**: Modular tool ecosystem based on Model Context Protocol
- 🔌 **Extensible Strategy Framework**: Support for third-party strategies and custom AI agent integration
- ⏰ **Historical Replay Capability**: Time-period replay functionality with automatic future information filtering

---

### 🎮 Trading Environment
Each AI model starts with $10,000, 100,000¥, or 50,000 USDT to trade NASDAQ 100 stocks, SSE 50 stocks, or major cryptocurrencies in a controlled environment with real market data and historical replay capabilities.

- 💰 **Initial Capital**: $10,000 USD (US stocks), 100,000¥ CNY (A-shares), or 50,000 USDT (cryptocurrencies) starting balance
- 📈 **Trading Universe**:
  - NASDAQ 100 component stocks (top 100 technology stocks)
  - SSE 50 component stocks
  - Major cryptocurrencies (BTC, ETH, XRP, SOL, ADA, SUI, LINK, AVAX, LTC, DOT)
- ⏰ **Trading Schedule**: Entire Week for cryptocurrencies, weekday market hours for stocks with historical simulation support
- 📊 **Data Integration**: Alpha Vantage API combined with Jina AI market intelligence
- 🔄 **Time Management**: Historical period replay with automated future information filtering

---

### 🧠 Agentic Trading Capabilities
AI agents operate with complete autonomy, conducting market research, making trading decisions, and continuously evolving their strategies without human intervention.

- 📰 **Autonomous Market Research**: Intelligent retrieval and filtering of market news, analyst reports, and financial data
- 💡 **Independent Decision Engine**: Multi-dimensional analysis driving fully autonomous buy/sell execution
- 📝 **Comprehensive Trade Logging**: Automated documentation of trading rationale, execution details, and portfolio changes
- 🔄 **Adaptive Strategy Evolution**: Self-optimizing algorithms that adjust based on market performance feedback

---

### 🏁 Competition Rules
All AI models compete under identical conditions with the same capital, data access, tools, and evaluation metrics to ensure fair comparison.

- 💰 **Starting Capital**: $10,000 USD or 100,000¥ CNY initial investment
- 📊 **Data Access**: Uniform market data and information feeds
- ⏰ **Operating Hours**: Synchronized trading time windows
- 📈 **Performance Metrics**: Standardized evaluation criteria across all models
- 🛠️ **Tool Access**: Identical MCP toolchain for all participants

🎯 **Objective**: Determine which AI model achieves superior investment returns through pure autonomous operation!

### 🚫 Zero Human Intervention
AI agents operate with complete autonomy, making all trading decisions and strategy adjustments without any human programming, guidance, or intervention.

- ❌ **No Pre-Programming**: Zero preset trading strategies or algorithmic rules
- ❌ **No Human Input**: Complete reliance on inherent AI reasoning capabilities
- ❌ **No Manual Override**: Absolute prohibition of human intervention during trading
- ✅ **Tool-Only Execution**: All operations executed exclusively through standardized tool calls
- ✅ **Self-Adaptive Learning**: Independent strategy refinement based on market performance feedback

---

## ⏰ Historical Replay Architecture

A core innovation of AI-Trader Bench is its **fully replayable** trading environment, ensuring scientific rigor and reproducibility in AI agent performance evaluation on historical market data.

### 🔄 Temporal Control Framework

#### 📅 Flexible Time Settings
```json
{
  "date_range": {
    "init_date": "2025-01-01",  // Any start date
    "end_date": "2025-01-31"    // Any end date
  }
}
```
---

### 🛡️ Anti-Look-Ahead Data Controls
AI can only access market data from current time and before. No future information allowed.

- 📊 **Price Data Boundaries**: Market data access limited to simulation timestamp and historical records
- 📰 **News Chronology Enforcement**: Real-time filtering prevents access to future-dated news and announcements
- 📈 **Financial Report Timeline**: Information restricted to officially published data as of current simulation date
- 🔍 **Historical Intelligence Scope**: Market analysis constrained to chronologically appropriate data availability

### 🎯 Replay Advantages

#### 🔬 Empirical Research Framework
- 📊 **Market Efficiency Studies**: Evaluate AI performance across diverse market conditions and volatility regimes
- 🧠 **Decision Consistency Analysis**: Examine temporal stability and behavioral patterns in AI trading logic
- 📈 **Risk Management Assessment**: Validate effectiveness of AI-driven risk mitigation strategies

#### 🎯 Fair Competition Framework
- 🏆 **Equal Information Access**: All AI models operate with identical historical datasets
- 📊 **Standardized Evaluation**: Performance metrics calculated using uniform data sources
- 🔍 **Full Reproducibility**: Complete experimental transparency with verifiable results

---

## 📁 Project Architecture

```
AI-Trader Bench/
├── 🤖 Core System
│   ├── main.py                    # 🎯 Main program entry
│   ├── agent/
│   │   ├── base_agent/            # 🧠 Generic AI trading agent (US stocks)
│   │   │   ├── base_agent.py      # Base agent class (daily)
│   │   │   ├── base_agent_hour.py # Hourly trading agent (US stocks)
│   │   │   └── __init__.py
│   │   ├── base_agent_astock/     # 🇨🇳 A-share specific trading agent
│   │   │   ├── base_agent_astock.py  # A-share agent class (daily)
│   │   │   ├── base_agent_astock_hour.py # A-share hourly trading agent
│   │   │   └── __init__.py
│   │   └── base_agent_crypto/     # ₿ Cryptocurrency specific trading agent
│   │       ├── base_agent_crypto.py # Crypto agent class
│   │       └── __init__.py
│   └── configs/                   # ⚙️ Configuration files
│
├── 🛠️ MCP Toolchain
│   ├── agent_tools/
│   │   ├── tool_trade.py          # 💰 Trade execution (auto-adapts market rules)
│   │   ├── tool_get_price_local.py # 📊 Price queries (supports US + A-shares)
│   │   ├── tool_jina_search.py   # 🔍 Information search
│   │   ├── tool_math.py           # 🧮 Mathematical calculations
│   │   └── start_mcp_services.py  # 🚀 MCP service startup script
│   └── tools/                     # 🔧 Auxiliary tools
│
├── 📊 Data System
│   ├── data/
│   │   ├── daily_prices_*.json    # 📈 NASDAQ 100 stock price data
│   │   ├── merged.jsonl           # 🔄 US stocks daily unified data format
│   │   ├── get_daily_price.py     # 📥 US stocks data fetching script
│   │   ├── merge_jsonl.py         # 🔄 US stocks data format conversion
│   │   ├── A_stock/               # 🇨🇳 A-share market data
│   │   │   ├── A_stock_data/              # 📁 A-share data storage directory
│   │   │   │   ├── sse_50_weight.csv          # 📋 SSE 50 constituent weights
│   │   │   │   ├── daily_prices_sse_50.csv    # 📈 Daily price data (CSV)
│   │   │   │   ├── A_stock_hourly.csv         # ⏰ 60-minute K-line data (CSV)
│   │   │   │   └── index_daily_sse_50.json    # 📊 SSE 50 index benchmark data
│   │   │   ├── merged.jsonl               # 🔄 A-share daily unified data format
│   │   │   ├── merged_hourly.jsonl        # ⏰ A-share hourly unified data format
│   │   │   ├── get_daily_price_tushare.py # 📥 A-share daily data fetching (Tushare API)
│   │   │   ├── get_daily_price_alphavantage.py # 📥 A-share daily data fetching (Alpha Vantage API)
│   │   │   ├── get_interdaily_price_astock.py # ⏰ A-share hourly data fetching (efinance)
│   │   │   ├── merge_jsonl_tushare.py     # 🔄 A-share daily data format conversion (Tushare API)
│   │   │   ├── merge_jsonl_alphavantage.py # 🔄 A-share daily data format conversion (Alpha Vantage API)
│   │   │   └── merge_jsonl_hourly.py      # ⏰ A-share hourly data format conversion (efinance)
│   │   ├── crypto/                # ₿ Cryptocurrency market data
│   │   │   ├── coin/                        # 📊 Individual crypto price files
│   │   │   │   ├── daily_prices_BTC.json   # Bitcoin price data
│   │   │   │   ├── daily_prices_ETH.json   # Ethereum price data
│   │   │   │   └── ...                      # Other cryptocurrency data
│   │   │   ├── crypto_merged.jsonl         # 🔄 Crypto unified data format
│   │   │   ├── get_daily_price_crypto.py   # 📥 Crypto data fetching script
│   │   │   └── merge_crypto_jsonl.py       # 🔄 Crypto data format conversion
│   │   ├── agent_data/            # 📝 AI trading records (NASDAQ 100)
│   │   ├── agent_data_astock/     # 📝 A-share AI trading records
│   │   └── agent_data_crypto/     # 📝 Cryptocurrency AI trading records
│   └── calculate_performance.py   # 📈 Performance analysis
│
├── ⚡ High Frequency Trading System
│   ├── main_hft.py                # 🚀 HFT main program entry
│   ├── futu/                      # 📡 Futu OpenD trading module
│   │   ├── opend_client.py        # 🔌 OpenD connection pool
│   │   ├── trade_executor.py      # 💹 Trade executor (long/short/flat)
│   │   ├── quote_subscriber.py    # 📊 Real-time quote subscriber
│   │   ├── session_manager.py     # ⏰ Trading session manager
│   │   └── options_trader.py      # 📈 Options trading support
│   ├── risk_control/              # 🛡️ Risk control module
│   │   ├── circuit_breaker.py     # ⚡ 3% daily loss circuit breaker
│   │   ├── drawdown_monitor.py    # 📉 Max drawdown ≤15% monitor
│   │   ├── slippage_checker.py    # 📏 Slippage ≤0.2% checker
│   │   ├── risk_manager.py        # 🎯 Comprehensive risk manager
│   │   └── performance_analyzer.py # 📊 Sharpe/fill rate/volume analyzer
│   ├── monitoring/                # 📈 Monitoring & alerting
│   │   ├── metrics_exporter.py    # 📤 Prometheus metrics exporter
│   │   ├── feishu_alert.py        # 💬 Feishu 5-min alert
│   │   └── grafana_dashboard.py   # 📊 Grafana dashboard config
│   ├── docker/                    # 🐳 Docker deployment
│   │   ├── Dockerfile             # Container build
│   │   ├── docker-compose.yml     # Stack: Trader + Prometheus + Grafana
│   │   └── prometheus.yml         # Prometheus config
│   └── tests/                     # 🧪 Unit & integration tests (14 files)
│       ├── test_trade_executor.py
│       ├── test_risk_control.py
│       ├── test_session_manager.py
│       ├── test_backtest.py       # 🆕 Backtest engine tests
│       ├── test_config_manager.py # 🆕 Config manager tests
│       └── test_integration.py
│
├── 📊 Backtest System             # 🆕 Historical data backtesting
│   └── backtest/
│       ├── backtest_engine.py     # 🔄 Backtest engine with metrics
│       └── __init__.py
│
├── 🌐 Web Dashboard               # 🆕 FastAPI real-time dashboard
│   └── web/
│       ├── dashboard.py           # 📊 WebSocket-powered UI
│       └── __init__.py
│
├── 📄 Report Generation           # 🆕 PDF/Excel report generation
│   └── reports/
│       ├── report_generator.py    # 📋 Multi-format reports
│       └── __init__.py
│
├── 💬 Prompt System
│   └── prompts/
│       ├── agent_prompt.py        # 🌐 Generic trading prompts (US stocks)
│       └── agent_prompt_astock.py # 🇨🇳 A-share specific trading prompts
│
├── 🎨 Frontend Interface
│   └── frontend/                  # 🌐 Web dashboard
│
├── 📋 Configuration & Documentation
│   ├── configs/                   # ⚙️ System configuration
│   │   ├── default_config.json    # US stocks default configuration
│   │   ├── astock_config.json     # A-share configuration example
│   │   ├── config_manager.py      # 🆕 Zero-deploy config system
│   │   └── hft_*.json             # 🆕 Pre-built HFT configs (TQQQ, SPXL, SOXL, AAPL, Options)
│   └── calc_perf.sh              # 🚀 Performance calculation script
│
└── 🚀 Quick Start Scripts
    └── scripts/                   # 🛠️ Convenient startup scripts (.sh + .bat)
        ├── main.sh/.bat           # One-click complete workflow (US stocks)
        ├── main_step1.sh/.bat     # US stocks: Data preparation
        ├── main_step2.sh/.bat     # US stocks: Start MCP services
        ├── main_step3.sh/.bat     # US stocks: Run trading agent
        ├── main_a_stock_step1.sh/.bat  # A-shares: Data preparation
        ├── main_a_stock_step2.sh/.bat  # A-shares: Start MCP services
        ├── main_a_stock_step3.sh  # A-shares: Run trading agent
        ├── main_crypto_step1.sh   # Crypto: Data preparation
        ├── main_crypto_step2.sh   # Crypto: Start MCP services
        ├── main_crypto_step3.sh   # Crypto: Run trading agent
        └── start_ui.sh            # Start web UI interface
```

### 🔧 Core Components Details

#### 🎯 Main Program (`main.py`)
- **Multi-Model Concurrency**: Run multiple AI models simultaneously for trading
- **Dynamic Agent Loading**: Automatically load corresponding agent type based on configuration
- **Configuration Management**: Support for JSON configuration files and environment variables
- **Date Management**: Flexible trading calendar and date range settings
- **Error Handling**: Comprehensive exception handling and retry mechanisms

#### 🤖 AI Agent System
| Agent Type | Module Path | Use Case | Features |
|-----------|-------------|----------|----------|
| **BaseAgent** | `agent.base_agent.base_agent` | US stocks daily trading | Flexible market switching, configurable stock pool |
| **BaseAgent_Hour** | `agent.base_agent.base_agent_hour` | US stocks hourly trading | Hourly data support, fine-grained trading timing |
| **BaseAgentAStock** | `agent.base_agent_astock.base_agent_astock` | A-shares daily trading | Built-in A-share rules, SSE 50 default pool, Chinese prompts |
| **BaseAgentAStock_Hour** | `agent.base_agent_astock.base_agent_astock_hour` | A-shares hourly trading | A-share hourly data (10:30/11:30/14:00/15:00), T+1 rules |
| **BaseAgentCrypto** | `agent.base_agent_crypto.base_agent_crypto` | Cryptocurrency trading | BITWISE10 crypto pool, USDT denominated |

**Architecture Advantages**:
- 🔄 **Clear Separation**: US, A-share, and cryptocurrency agents independently maintained without interference
- 🎯 **Specialized Optimization**: Each agent deeply optimized for specific market characteristics
- 🔌 **Easy Extension**: Support adding more market-specific agents (e.g., Hong Kong stocks, commodities)

#### 🛠️ MCP Toolchain
| Tool | Function | Market Support | API |
|------|----------|----------------|-----|
| **Trading Tool** | Buy/sell assets, position management | 🇺🇸 US / 🇨🇳 A-shares / ₿ Crypto | `buy()`, `sell()` / `buy_crypto()`, `sell_crypto()` (For Crypto)|
| **Price Tool** | Real-time and historical price queries | 🇺🇸 US / 🇨🇳 A-shares / ₿ Crypto | `get_price_local()` |
| **Search Tool** | Market information search | Global markets | `get_information()` |
| **Math Tool** | Financial calculations and analysis | Generic | Basic mathematical operations |

**Tool Features**:
- 🔍 **Auto-Recognition**: Automatically select data source based on symbol format (stock codes or crypto symbols)
- 📏 **Rule Adaptation**: Auto-apply corresponding market trading rules (T+0/T+1, lot sizes etc.)
- 🌐 **Unified Interface**: Same API interface supports multi-market trading across stocks and cryptocurrencies

#### 📊 Data System
- **📈 Price Data**:
  - 🇺🇸 Complete OHLCV data for NASDAQ 100 component stocks (Alpha Vantage)
  - 🇨🇳 A-share market data (SSE 50 Index) via Tushare API
  - ₿ Cryptocurrency market data (BITWISE10) via Alpha Vantage
  - 📁 Unified JSONL format for efficient reading
- **📝 Trading Records**:
  - Detailed trading history for each AI model
  - Stored separately by market: `agent_data/` (US), `agent_data_astock/` (A-shares), `agent_data_crypto/` (Crypto)
- **📊 Performance Metrics**:
  - Sharpe ratio, maximum drawdown, annualized returns, etc.
  - Support multi-market performance comparison analysis
- **🔄 Data Synchronization**:
  - Automated data acquisition and update mechanisms
  - Independent data fetching scripts with incremental update support

## 🚀 Quick Start

### 📋 Prerequisites


- **Python 3.10+** 
- **API Keys**: 
  - OpenAI (for AI models)
  - Alpha Vantage (for NASDAQ 100 data)
  - Jina AI (for market information search)
  - Tushare (for A-share market data, optional)

### ⚡ One-Click Installation

```bash
# 1. Clone project
git clone https://github.com/HKUDS/AI-Trader.git
cd AI-Trader

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment variables
cp .env.example .env
# Edit .env file and fill in your API keys
```

### 🔑 Environment Configuration

Create `.env` file and configure the following variables:

```bash
# 🤖 AI Model API Configuration
OPENAI_API_BASE=https://your-openai-proxy.com/v1
OPENAI_API_KEY=your_openai_key

# 📊 Data Source Configuration
ALPHAADVANTAGE_API_KEY=your_alpha_vantage_key  # For NASDAQ 100 and cryptocurrency data
JINA_API_KEY=your_jina_api_key
TUSHARE_TOKEN=your_tushare_token               # For A-share data

# ⚙️ System Configuration
RUNTIME_ENV_PATH=./runtime_env.json # Recommended to use absolute path

# 🌐 Service Port Configuration
MATH_HTTP_PORT=8000
SEARCH_HTTP_PORT=8001
TRADE_HTTP_PORT=8002
GETPRICE_HTTP_PORT=8003
CRYPTO_HTTP_PORT=8005

# 🧠 AI Agent Configuration
AGENT_MAX_STEP=30             # Maximum reasoning steps
```

### 📦 Dependencies

```bash
# Install production dependencies
pip install -r requirements.txt

# Or manually install core dependencies
pip install langchain langchain-openai langchain-mcp-adapters fastmcp python-dotenv requests numpy pandas tushare
```

## 🎮 Running Guide

### 🚀 Quick Start with Scripts

We provide convenient shell scripts in the `scripts/` directory for easy startup:

#### 🇺🇸 US Market (NASDAQ 100)
```bash
# One-click startup (complete workflow)
bash scripts/main.sh

# Or run step by step:
bash scripts/main_step1.sh  # Step 1: Prepare data
bash scripts/main_step2.sh  # Step 2: Start MCP services
bash scripts/main_step3.sh  # Step 3: Run trading agent
```

#### 🇨🇳 A-Share Market (SSE 50)
```bash
# Run step by step:
bash scripts/main_a_stock_step1.sh  # Step 1: Prepare A-share data
bash scripts/main_a_stock_step2.sh  # Step 2: Start MCP services
bash scripts/main_a_stock_step3.sh  # Step 3: Run A-share trading agent
```

#### ₿ Cryptocurrency Market (BITWISE10)
```bash
# Run step by step:
bash scripts/main_crypto_step1.sh  # Step 1: Prepare crypto data
bash scripts/main_crypto_step2.sh  # Step 2: Start MCP services
bash scripts/main_crypto_step3.sh  # Step 3: Run crypto trading agent
```

#### 🌐 Web UI
```bash
# Start web interface
bash scripts/start_ui.sh
# Visit: http://localhost:8888
```

---

### 📋 Manual Setup Guide

If you prefer to run commands manually, follow these steps:

### 📊 Step 1: Data Preparation

#### 🇺🇸 NASDAQ 100 Data

```bash
# 📈 Get NASDAQ 100 stock data
cd data
python get_daily_price.py

# 🔄 Merge data into unified format
python merge_jsonl.py
```

#### 🇨🇳 A-Share Market Data (SSE 50)

```bash
# 📈 Get Chinese A-share daily market data (SSE 50 Index)
cd data/A_stock

# 📈 Method 1: Get daily data using Tushare API (Recommended)
python get_daily_price_tushare.py
python merge_jsonl_tushare.py

# 📈 Method 2: Get daily data using Alpha Vantage API (Alternative)
python get_daily_price_alphavantage.py
python merge_jsonl_alphavantage.py

# 📊 Daily data will be saved to: data/A_stock/merged.jsonl

# ⏰ Get 60-minute K-line data (hourly trading)
python get_interdaily_price_astock.py
python merge_jsonl_hourly.py

# 📊 Hourly data will be saved to: data/A_stock/merged_hourly.jsonl
```

#### ₿ Cryptocurrency Market Data (BITWISE10)

```bash
# 📈 Get cryptocurrency market data (BITWISE10)
cd data/crypto

# 📊 Get daily price data for major cryptocurrencies
python get_daily_price_crypto.py

# 🔄 Merge data into unified format
python merge_crypto_jsonl.py

# 📊 Crypto data will be saved to: data/crypto/crypto_merged.jsonl
```


### 🛠️ Step 2: Start MCP Services

```bash
cd ./agent_tools
python start_mcp_services.py
```

### 🚀 Step 3: Start AI Arena

#### For US Stocks (NASDAQ 100):
```bash
# 🎯 Run with default configuration
python main.py

# 🎯 Or specify US stock config
python main.py configs/default_config.json
```

#### For A-Shares (SSE 50):
```bash
# 🎯 Run A-share trading
python main.py configs/astock_config.json
```

#### For Cryptocurrencies (BITWISE10):
```bash
# 🎯 Run cryptocurrency trading
python main.py configs/default_crypto_config.json
```

#### ⚡ For High Frequency Trading (HFT):
```bash
# 🚀 Prerequisites: Install HFT dependencies
pip install futu-api aiohttp pytz prometheus-client

# 🔧 Start Futu OpenD (download from https://www.futunn.com/download/openAPI)
# Configure your OpenD with trading password

# 📝 Configure environment variables
export OPEND_HOST=127.0.0.1
export OPEND_PORT=11111
export OPEND_TRD_ENV=1  # 1=Simulation, 0=Live
export FEISHU_WEBHOOK_URL=your_webhook_url  # Optional

# 🎯 Run HFT in simulation mode (TQQQ/QQQ)
python main_hft.py --symbols TQQQ QQQ --dry-run

# 🎯 Run HFT with custom symbols
python main_hft.py --symbols SPXL SOXL AAPL --dry-run

# 🎯 Run HFT with custom config
python main_hft.py --config configs/hft_config.json --dry-run

# 🐳 Docker deployment
cd docker
docker-compose up -d
# Access Grafana: http://localhost:3000 (admin/admin123)
# Access Prometheus: http://localhost:9091
```

**HFT Performance Targets:**
| Metric | Target | Description |
|--------|--------|-------------|
| Order Latency | ≤ 0.0014s | Ultra-fast order execution |
| Full Loop | ≤ 1s | Quote → Decision → Order |
| Slippage | ≤ 0.2% | Execution price deviation |
| Sharpe Ratio | ≥ 2.0 | Risk-adjusted returns |
| Max Drawdown | ≤ 15% | Capital protection |
| Daily Volume | ≥ $50,000 | Trading activity |
| Fill Rate | ≥ 95% | Order completion rate |

### ⏰ Time Settings Example

#### 📅 US Stock Configuration Example (Using BaseAgent)
```json
{
  "agent_type": "BaseAgent",
  "market": "us",              // Market type: "us" for US stocks
  "date_range": {
    "init_date": "2024-01-01",  // Backtest start date
    "end_date": "2024-03-31"     // Backtest end date
  },
  "models": [
    {
      "name": "claude-3.7-sonnet",
      "basemodel": "anthropic/claude-3.7-sonnet",
      "signature": "claude-3.7-sonnet",
      "enabled": true
    }
  ],
  "agent_config": {
    "initial_cash": 10000.0    // Initial capital: $10,000
  }
}
```

#### 📅 A-Share Daily Configuration Example (Using BaseAgentAStock)
```json
{
  "agent_type": "BaseAgentAStock",  // A-share daily specific agent
  "market": "cn",                   // Market type: "cn" A-shares (optional, will be ignored, always uses cn)
  "date_range": {
    "init_date": "2025-10-09",      // Backtest start date
    "end_date": "2025-10-31"         // Backtest end date
  },
  "models": [
    {
      "name": "claude-3.7-sonnet",
      "basemodel": "anthropic/claude-3.7-sonnet",
      "signature": "claude-3.7-sonnet",
      "enabled": true
    }
  ],
  "agent_config": {
    "initial_cash": 100000.0        // Initial capital: ¥100,000
  },
  "log_config": {
    "log_path": "./data/agent_data_astock"  // A-share daily data path
  }
}
```

#### 📅 A-Share Hourly Configuration Example (Using BaseAgentAStock_Hour)
```json
{
  "agent_type": "BaseAgentAStock_Hour",  // A-share hourly specific agent
  "market": "cn",                        // Market type: "cn" A-shares (optional, will be ignored, always uses cn)
  "date_range": {
    "init_date": "2025-10-09 10:30:00",  // Backtest start time (hourly)
    "end_date": "2025-10-31 15:00:00"    // Backtest end time (hourly)
  },
  "models": [
    {
      "name": "claude-3.7-sonnet",
      "basemodel": "anthropic/claude-3.7-sonnet",
      "signature": "claude-3.7-sonnet-astock-hour",
      "enabled": true
    }
  ],
  "agent_config": {
    "initial_cash": 100000.0        // Initial capital: ¥100,000
  },
  "log_config": {
    "log_path": "./data/agent_data_astock_hour"  // A-share hourly data path
  }
}
```

> 💡 **Tip**: A-share hourly trading time points: 10:30, 11:30, 14:00, 15:00 (4 time points per day)

> 💡 **Tip**: When using `BaseAgentAStock` or `BaseAgentAStock_Hour`, the `market` parameter is automatically set to `"cn"` and doesn't need to be specified manually.

#### 📅 Cryptocurrency Configuration Example (Using BaseAgentCrypto)
```json
{
  "agent_type": "BaseAgentCrypto",  // Cryptocurrency specific agent
  "market": "crypto",               // Market type: "crypto" for cryptocurrencies
  "date_range": {
    "init_date": "2025-10-20",      // Backtest start date
    "end_date": "2025-10-31"         // Backtest end date
  },
  "models": [
    {
      "name": "claude-3.7-sonnet",
      "basemodel": "anthropic/claude-3.7-sonnet",
      "signature": "claude-3.7-sonnet",
      "enabled": true
    }
  ],
  "agent_config": {
    "initial_cash": 50000.0        // Initial capital: 50,000 USDT
  },
  "log_config": {
    "log_path": "./data/agent_data_crypto" // crypto daily data path
  }
}
```
> 💡 **Tip**: `BaseAgentCrypto` will use the price at UTC 00:00 as the buy/sell price. The market should be set to `"crypto"`.

### 📈 Start Web Interface

```bash
cd docs
python3 -m http.server 8000
# Visit http://localhost:8000
```

## 📈 Performance Analysis

### 🏆 Competition Rules

| Rule Item | US Stocks | A-Shares (China) | Cryptocurrencies |
|-----------|-----------|------------------|------------------|
| **💰 Initial Capital** | $10,000 | ¥100,000 | 50,000 USDT |
| **📈 Trading Targets** | NASDAQ 100 | SSE 50 | BITWISE10 Top Cryptocurrencies |
| **🌍 Market** | US Stock Market | China A-Share Market | Global Crypto Market |
| **⏰ Trading Hours** | Weekdays | Weekdays | Entire Week |
| **💲 Price Benchmark** | Opening Price | Opening Price | Opening Price |
| **📝 Recording Method** | JSONL Format | JSONL Format | JSONL Format |

## ⚙️ Configuration Guide

### 📋 Configuration File Structure

```json
{
  "agent_type": "BaseAgent",
  "market": "us",
  "date_range": {
    "init_date": "2025-10-01",
    "end_date": "2025-10-30"
  },
  "models": [
    {
      "name": "claude-3.7-sonnet",
      "basemodel": "anthropic/claude-3.7-sonnet",
      "signature": "claude-3.7-sonnet",
      "enabled": true
    }
  ],
  "agent_config": {
    "max_steps": 30,
    "max_retries": 3,
    "base_delay": 1.0,
    "initial_cash": 10000.0
  },
  "log_config": {
    "log_path": "./data/agent_data"
  }
}
```

### 🔧 Configuration Parameters

| Parameter | Description | Options | Default Value |
|-----------|-------------|---------|---------------|
| `agent_type` | AI agent type | "BaseAgent" (generic)<br>"BaseAgentAStock" (A-share specific) | "BaseAgent" |
| `market` | Market type | "us" (US stocks)<br>"cn" (A-shares)<br>"crypto" (Cryptocurrency)<br>Note: Auto-set to "cn" when using BaseAgentAStock, "crypto" when using BaseAgentCrypto | "us" |
| `max_steps` | Maximum reasoning steps | Positive integer | 30 |
| `max_retries` | Maximum retry attempts | Positive integer | 3 |
| `base_delay` | Operation delay (seconds) | Float | 1.0 |
| `initial_cash` | Initial capital | Float | $10,000 (US)<br>¥100,000 (A-shares) <br> 50,000-USDT (Cryptocurrency) |

#### 📋 Agent Type Details

| Agent Type | Applicable Markets | Trading Frequency | Features |
|-----------|-------------------|------------------|----------|
| **BaseAgent** | US stocks | Daily | • Generic trading agent<br>• Switch markets via `market` parameter<br>• Flexible stock pool configuration |
| **BaseAgent_Hour** | US stocks | Hourly | • US stocks hourly trading<br>• Fine-grained trading timing control<br>• Supports intraday trading decisions |
| **BaseAgentAStock** | A-shares | Daily | • Optimized for A-share daily trading<br>• Built-in A-share trading rules (100-share lots, T+1)<br>• Default SSE 50 stock pool<br>• Chinese Yuan pricing |
| **BaseAgentAStock_Hour** | A-shares | Hourly | • A-share hourly trading (10:30/11:30/14:00/15:00)<br>• Supports 4 intraday time points<br>• Inherits all A-share trading rules<br>• Data source: merged_hourly.jsonl |
| **BaseAgentCrypto** | Cryptocurrencies | Daily | • Optimized for cryptocurrencies<br>• Default BITWISE10 index pool<br>• USDT pricing<br>• Supports entire week trading |

### 📊 Data Format

#### 💰 Position Records (position.jsonl)
```json
{
  "date": "2025-01-20",
  "id": 1,
  "this_action": {
    "action": "buy",
    "symbol": "AAPL", 
    "amount": 10
  },
  "positions": {
    "AAPL": 10,
    "MSFT": 0,
    "CASH": 9737.6
  }
}
```

#### 📈 Price Data (merged.jsonl)
```json
{
  "Meta Data": {
    "2. Symbol": "AAPL",
    "3. Last Refreshed": "2025-01-20"
  },
  "Time Series (Daily)": {
    "2025-01-20": {
      "1. buy price": "255.8850",
      "2. high": "264.3750", 
      "3. low": "255.6300",
      "4. sell price": "262.2400",
      "5. volume": "90483029"
    }
  }
}
```

### 📁 File Structure

```
data/agent_data/
├── claude-3.7-sonnet/
│   ├── position/
│   │   └── position.jsonl      # 📝 Position records
│   └── log/
│       └── 2025-01-20/
│           └── log.jsonl       # 📊 Trading logs
├── gpt-4o/
│   └── ...
└── qwen3-max/
    └── ...
```

## 🔌 Third-Party Strategy Integration

AI-Trader Bench adopts a modular design, supporting easy integration of third-party strategies and custom AI agents.

### 🛠️ Integration Methods

#### 1. Custom AI Agent
```python
# Create new AI agent class
class CustomAgent(BaseAgent):
    def __init__(self, model_name, **kwargs):
        super().__init__(model_name, **kwargs)
        # Add custom logic
```

#### 2. Register New Agent
```python
# Register in main.py
AGENT_REGISTRY = {
    "BaseAgent": {
        "module": "agent.base_agent.base_agent",
        "class": "BaseAgent"
    },
    "BaseAgentAStock": {
        "module": "agent.base_agent_astock.base_agent_astock",
        "class": "BaseAgentAStock"
    },
    "CustomAgent": {  # New custom agent
        "module": "agent.custom.custom_agent",
        "class": "CustomAgent"
    },
}
```

#### 3. Configuration File Settings
```json
{
  "agent_type": "CustomAgent",
  "models": [
    {
      "name": "your-custom-model",
      "basemodel": "your/model/path",
      "signature": "custom-signature",
      "enabled": true
    }
  ]
}
```

### 🔧 Extending Toolchain

#### Adding Custom Tools
```python
# Create new MCP tool
@mcp.tools()
class CustomTool:
    def __init__(self):
        self.name = "custom_tool"
    
    def execute(self, params):
        # Implement custom tool logic
        return result
```

## 🚀 Roadmap

### 🌟 Future Plans
- [x] **🇨🇳 A-Share Support** - ✅ SSE 50 Index data integration completed
- [x] **₿ Cryptocurrency** - ✅ BITWISE10 digital currency trading support completed
- [ ] **📊 Post-Market Statistics** - Automatic profit analysis
- [ ] **🔌 Strategy Marketplace** - Add third-party strategy sharing platform
- [ ] **🎨 Cool Frontend Interface** - Modern web dashboard
- [ ] **📈 More Strategies** - Technical analysis, quantitative strategies
- [ ] **⏰ Advanced Replay** - Support minute-level time precision and real-time replay
- [ ] **🔍 Smart Filtering** - More precise future information detection and filtering


## 📞 Support & Community

- **💬 Discussions**: [GitHub Discussions](https://github.com/HKUDS/AI-Trader/discussions)
- **🐛 Issues**: [GitHub Issues](https://github.com/HKUDS/AI-Trader/issues)

## 📄 License

This project is licensed under the [MIT License](LICENSE).

## 🙏 Acknowledgments

Thanks to the following open source projects and services:
- [LangChain](https://github.com/langchain-ai/langchain) - AI application development framework
- [MCP](https://github.com/modelcontextprotocol) - Model Context Protocol
- [Alpha Vantage](https://www.alphavantage.co/) - US stock financial data API
- [Tushare](https://tushare.pro/) - China A-share market data API
- [efinance](https://github.com/Micro-sheep/efinance) - A-share hourly data acquisition
- [Jina AI](https://jina.ai/) - Information search service

## 👥 Administrator

<div align="center">

<a href="https://github.com/TianyuFan0504">
  <img src="https://avatars.githubusercontent.com/TianyuFan0504?v=4" width="80" height="80" alt="TianyuFan0504" style="border-radius: 50%; margin: 5px;"/>
</a>
<a href="https://github.com/yangqin-jiang">
  <img src="https://avatars.githubusercontent.com/yangqin-jiang?v=4" width="80" height="80" alt="yangqin-jiang" style="border-radius: 50%; margin: 5px;"/>
</a>
<a href="https://github.com/yuh-yang">
  <img src="https://avatars.githubusercontent.com/yuh-yang?v=4" width="80" height="80" alt="yuh-yang" style="border-radius: 50%; margin: 5px;"/>
</a>
<a href="https://github.com/Hoder-zyf">
  <img src="https://avatars.githubusercontent.com/Hoder-zyf?v=4" width="80" height="80" alt="Hoder-zyf" style="border-radius: 50%; margin: 5px;"/>
</a>

</div>

## 🤝 Contribution

<div align="center">
  We thank all our contributors for their valuable contributions.
</div>

<div align="center">
  <a href="https://github.com/HKUDS/AI-Trader/graphs/contributors">
    <img src="https://contrib.rocks/image?repo=HKUDS/AI-Trader" style="border-radius: 15px; box-shadow: 0 0 20px rgba(0, 217, 255, 0.3);" />
  </a>
</div>

## Disclaimer

The materials provided by the AI-Trader project are for research purposes only and do not constitute any investment advice. Investors should seek independent professional advice before making any investment decisions. Past performance, if any, should not be taken as an indicator of future results. You should note that the value of investments may go up as well as down, and there is no guarantee of returns. All content of the AI-Trader project is provided solely for research purposes and does not constitute a recommendation to invest in any of the mentioned securities or sectors. Investing involves risks. Please seek professional advice if needed.

---

<div align="center">

**🌟 If this project helps you, please give us a Star!**

[![GitHub stars](https://img.shields.io/github/stars/HKUDS/AI-Trader?style=social)](https://github.com/HKUDS/AI-Trader)
[![GitHub forks](https://img.shields.io/github/forks/HKUDS/AI-Trader?style=social)](https://github.com/HKUDS/AI-Trader)

**🤖 Experience AI's full potential in financial markets through complete autonomous decision-making!**  
**🛠️ Pure tool-driven execution with zero human intervention—a genuine AI trading arena!** 🚀

</div>

---

## ⚡ High Frequency Trading System

### System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    AI-Trader HFT System                     │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │  Quote Sub  │  │  AI Model   │  │  Executor   │         │
│  │  (1min K)   │──│  Decision   │──│  (OpenD)    │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
│         │                │                │                 │
│         ▼                ▼                ▼                 │
│  ┌─────────────────────────────────────────────────┐       │
│  │              Risk Control Layer                  │       │
│  │  • Circuit Breaker (3% daily loss)              │       │
│  │  • Drawdown Monitor (≤15% max)                  │       │
│  │  • Slippage Checker (≤0.2%)                     │       │
│  └─────────────────────────────────────────────────┘       │
│         │                                                   │
│         ▼                                                   │
│  ┌─────────────────────────────────────────────────┐       │
│  │              Monitoring & Alerting               │       │
│  │  • Prometheus Metrics (port 9090)               │       │
│  │  • Grafana Dashboard                            │       │
│  │  • Feishu Alert (5-min notification)            │       │
│  └─────────────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────────────┘
```

### Key Features

| Feature | Description |
|---------|-------------|
| **Futu OpenD Integration** | Direct connection to Futu trading platform |
| **Session Manager** | Pre-market, regular, after-hours seamless trading |
| **Options Support** | Straddle, strangle, bull/bear spread strategies |
| **Performance Analyzer** | Real-time Sharpe, Sortino, drawdown calculation |
| **Zero-Change Deployment** | Same code for TQQQ, SPXL, SOXL, AAPL, options |

### Running Tests

```bash
# Run all tests with coverage
python run_tests.py

# Quick tests (excluding integration)
python run_tests.py --quick

# Coverage analysis (target ≥80%)
python run_tests.py --coverage
```

### Documentation

- 📖 [HFT System Guide](docs/HFT_README.md) - Detailed HFT documentation
- 🔄 [Git Flow Guide](docs/GIT_FLOW.md) - Development workflow
- ⚙️ [HFT Configuration](configs/hft_config.json) - HFT settings

---

## ⭐ Star History

*Community Growth Trajectory*

<div align="center">
  <a href="https://star-history.com/#HKUDS/AI-Trader&Date">
    <picture>
      <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=HKUDS/AI-Trader&type=Date&theme=dark" />
      <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=HKUDS/AI-Trader&type=Date" />
      <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=HKUDS/AI-Trader&type=Date" style="border-radius: 15px; box-shadow: 0 0 30px rgba(0, 217, 255, 0.3);" />
    </picture>
  </a>
</div>

---


## 🌟Citation

```python
@article{fan2025ai,
  title={AI-Trader: Benchmarking Autonomous Agents in Real-Time Financial Markets},
  author={Fan, Tianyu and Yang, Yuhao and Jiang, Yangqin and Zhang, Yifei and Chen, Yuxuan and Huang, Chao},
  journal={arXiv preprint arXiv:2512.10971},
  year={2025}
}
```


<p align="center">
  <em> ❤️ Thanks for visiting ✨ AI-Trader!</em><br><br>
  <img src="https://visitor-badge.laobi.icu/badge?page_id=HKUDS.AI-Trader&style=for-the-badge&color=00d4ff" alt="Views">
</p>
