# -*- coding: utf-8 -*-
"""
统一配置管理
支持零改动部署到任意美股标的
"""

import json
import os
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class TradingConfig:
    """交易配置"""
    symbols: List[str] = field(default_factory=lambda: ["TQQQ", "QQQ"])
    initial_cash: float = 50000.0
    trading_interval: int = 60  # 秒
    enable_premarket: bool = True
    enable_afterhours: bool = True
    max_position_pct: float = 0.25
    order_type: str = "limit"  # market/limit


@dataclass
class RiskConfig:
    """风控配置"""
    max_drawdown: float = 0.15  # 15%
    daily_loss_limit: float = 0.03  # 3%
    max_slippage: float = 0.002  # 0.2%
    position_limit: int = 1000
    enable_circuit_breaker: bool = True


@dataclass
class ConnectionConfig:
    """连接配置"""
    opend_host: str = "127.0.0.1"
    opend_port: int = 11111
    trd_env: int = 1  # 0=真实, 1=模拟
    trade_password: str = ""
    pool_size: int = 3


@dataclass
class MonitoringConfig:
    """监控配置"""
    metrics_port: int = 9090
    enable_feishu: bool = True
    feishu_webhook: str = ""
    alert_interval: int = 300  # 5分钟
    enable_grafana: bool = True


@dataclass
class ModelConfig:
    """模型配置"""
    name: str = "gpt-4"
    base_url: str = ""
    api_key: str = ""
    max_tokens: int = 1000
    temperature: float = 0.7


@dataclass
class HFTConfig:
    """高频交易完整配置"""
    trading: TradingConfig = field(default_factory=TradingConfig)
    risk: RiskConfig = field(default_factory=RiskConfig)
    connection: ConnectionConfig = field(default_factory=ConnectionConfig)
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)
    model: ModelConfig = field(default_factory=ModelConfig)
    dry_run: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trading": asdict(self.trading),
            "risk": asdict(self.risk),
            "connection": asdict(self.connection),
            "monitoring": asdict(self.monitoring),
            "model": asdict(self.model),
            "dry_run": self.dry_run
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "HFTConfig":
        config = cls()

        if "trading" in data:
            for k, v in data["trading"].items():
                if hasattr(config.trading, k):
                    setattr(config.trading, k, v)

        if "risk" in data:
            for k, v in data["risk"].items():
                if hasattr(config.risk, k):
                    setattr(config.risk, k, v)

        if "connection" in data:
            for k, v in data["connection"].items():
                if hasattr(config.connection, k):
                    setattr(config.connection, k, v)

        if "monitoring" in data:
            for k, v in data["monitoring"].items():
                if hasattr(config.monitoring, k):
                    setattr(config.monitoring, k, v)

        if "model" in data:
            for k, v in data["model"].items():
                if hasattr(config.model, k):
                    setattr(config.model, k, v)

        if "dry_run" in data:
            config.dry_run = data["dry_run"]

        return config

    def save(self, filepath: str):
        """保存配置到文件"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
        logger.info(f"Config saved to {filepath}")

    @classmethod
    def load(cls, filepath: str) -> "HFTConfig":
        """从文件加载配置"""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return cls.from_dict(data)

    def apply_env_overrides(self):
        """从环境变量覆盖配置"""
        # 连接配置
        if os.getenv("OPEND_HOST"):
            self.connection.opend_host = os.getenv("OPEND_HOST")
        if os.getenv("OPEND_PORT"):
            self.connection.opend_port = int(os.getenv("OPEND_PORT"))
        if os.getenv("OPEND_TRD_ENV"):
            self.connection.trd_env = int(os.getenv("OPEND_TRD_ENV"))
        if os.getenv("OPEND_TRADE_PASSWORD"):
            self.connection.trade_password = os.getenv("OPEND_TRADE_PASSWORD")

        # 监控配置
        if os.getenv("FEISHU_WEBHOOK_URL"):
            self.monitoring.feishu_webhook = os.getenv("FEISHU_WEBHOOK_URL")
            self.monitoring.enable_feishu = True

        # 模型配置
        if os.getenv("OPENAI_API_KEY"):
            self.model.api_key = os.getenv("OPENAI_API_KEY")
        if os.getenv("OPENAI_API_BASE"):
            self.model.base_url = os.getenv("OPENAI_API_BASE")


# 预定义配置模板

def get_tqqq_qqq_config() -> HFTConfig:
    """TQQQ/QQQ 配置（默认）"""
    config = HFTConfig()
    config.trading.symbols = ["TQQQ", "QQQ"]
    return config


def get_spxl_config() -> HFTConfig:
    """SPXL 配置"""
    config = HFTConfig()
    config.trading.symbols = ["SPXL", "UPRO", "SPY"]
    config.trading.max_position_pct = 0.3
    return config


def get_soxl_config() -> HFTConfig:
    """SOXL 配置（半导体）"""
    config = HFTConfig()
    config.trading.symbols = ["SOXL", "SOXS", "SMH"]
    config.trading.max_position_pct = 0.2  # 波动大，降低仓位
    config.risk.daily_loss_limit = 0.02  # 更严格的止损
    return config


def get_aapl_config() -> HFTConfig:
    """AAPL 配置"""
    config = HFTConfig()
    config.trading.symbols = ["AAPL"]
    config.trading.max_position_pct = 0.5  # 单标的可以更高
    config.risk.max_slippage = 0.001  # 大盘股滑点更小
    return config


def get_options_config() -> HFTConfig:
    """期权配置"""
    config = HFTConfig()
    config.trading.symbols = ["SPY", "QQQ", "AAPL"]  # 底层标的
    config.trading.max_position_pct = 0.1  # 期权风险大
    config.risk.daily_loss_limit = 0.02
    config.risk.max_drawdown = 0.10
    return config


def get_multi_stock_config(symbols: List[str]) -> HFTConfig:
    """多标的配置"""
    config = HFTConfig()
    config.trading.symbols = symbols
    config.trading.max_position_pct = min(0.25, 1.0 / len(symbols))
    return config


# 配置注册表
CONFIG_REGISTRY = {
    "tqqq_qqq": get_tqqq_qqq_config,
    "spxl": get_spxl_config,
    "soxl": get_soxl_config,
    "aapl": get_aapl_config,
    "options": get_options_config,
}


def get_config(name: str = "tqqq_qqq") -> HFTConfig:
    """获取预定义配置"""
    if name in CONFIG_REGISTRY:
        return CONFIG_REGISTRY[name]()
    else:
        logger.warning(f"Unknown config: {name}, using default")
        return HFTConfig()


def generate_all_configs(output_dir: str = "./configs"):
    """生成所有预定义配置文件"""
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    for name, factory in CONFIG_REGISTRY.items():
        config = factory()
        filepath = Path(output_dir) / f"hft_{name}_config.json"
        config.save(str(filepath))
        print(f"Generated: {filepath}")


if __name__ == "__main__":
    # 生成所有配置
    generate_all_configs()
