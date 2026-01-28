# -*- coding: utf-8 -*-
"""
配置管理单元测试
"""

import os
import pytest
import tempfile
import json

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from configs.config_manager import (
    TradingConfig, RiskConfig, ConnectionConfig, MonitoringConfig, ModelConfig,
    HFTConfig, get_config, get_tqqq_qqq_config, get_spxl_config, get_soxl_config,
    get_aapl_config, get_options_config, get_multi_stock_config, CONFIG_REGISTRY
)


class TestTradingConfig:
    """交易配置测试"""

    def test_default_values(self):
        """测试默认值"""
        config = TradingConfig()

        assert "TQQQ" in config.symbols
        assert config.initial_cash == 50000.0
        assert config.trading_interval == 60
        assert config.enable_premarket == True


class TestRiskConfig:
    """风控配置测试"""

    def test_default_values(self):
        """测试默认值"""
        config = RiskConfig()

        assert config.max_drawdown == 0.15
        assert config.daily_loss_limit == 0.03
        assert config.max_slippage == 0.002
        assert config.enable_circuit_breaker == True


class TestConnectionConfig:
    """连接配置测试"""

    def test_default_values(self):
        """测试默认值"""
        config = ConnectionConfig()

        assert config.opend_host == "127.0.0.1"
        assert config.opend_port == 11111
        assert config.trd_env == 1  # 模拟环境


class TestHFTConfig:
    """HFT 完整配置测试"""

    def test_default_config(self):
        """测试默认配置"""
        config = HFTConfig()

        assert config.trading is not None
        assert config.risk is not None
        assert config.connection is not None
        assert config.monitoring is not None
        assert config.model is not None
        assert config.dry_run == True

    def test_to_dict(self):
        """测试转字典"""
        config = HFTConfig()
        d = config.to_dict()

        assert "trading" in d
        assert "risk" in d
        assert "connection" in d
        assert "monitoring" in d
        assert "model" in d
        assert d["dry_run"] == True

    def test_from_dict(self):
        """测试从字典创建"""
        data = {
            "trading": {"symbols": ["AAPL", "MSFT"], "initial_cash": 100000},
            "risk": {"max_drawdown": 0.10},
            "dry_run": False
        }

        config = HFTConfig.from_dict(data)

        assert config.trading.symbols == ["AAPL", "MSFT"]
        assert config.trading.initial_cash == 100000
        assert config.risk.max_drawdown == 0.10
        assert config.dry_run == False

    def test_save_and_load(self):
        """测试保存和加载"""
        config = HFTConfig()
        config.trading.symbols = ["TEST1", "TEST2"]
        config.risk.max_drawdown = 0.20

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            filepath = f.name

        try:
            config.save(filepath)

            loaded = HFTConfig.load(filepath)

            assert loaded.trading.symbols == ["TEST1", "TEST2"]
            assert loaded.risk.max_drawdown == 0.20
        finally:
            os.unlink(filepath)

    def test_apply_env_overrides(self):
        """测试环境变量覆盖"""
        config = HFTConfig()

        # 设置环境变量
        os.environ["OPEND_HOST"] = "192.168.1.100"
        os.environ["OPEND_PORT"] = "22222"

        try:
            config.apply_env_overrides()

            assert config.connection.opend_host == "192.168.1.100"
            assert config.connection.opend_port == 22222
        finally:
            # 清理环境变量
            del os.environ["OPEND_HOST"]
            del os.environ["OPEND_PORT"]


class TestPresetConfigs:
    """预设配置测试"""

    def test_tqqq_qqq_config(self):
        """测试 TQQQ/QQQ 配置"""
        config = get_tqqq_qqq_config()

        assert "TQQQ" in config.trading.symbols
        assert "QQQ" in config.trading.symbols

    def test_spxl_config(self):
        """测试 SPXL 配置"""
        config = get_spxl_config()

        assert "SPXL" in config.trading.symbols
        assert config.trading.max_position_pct == 0.3

    def test_soxl_config(self):
        """测试 SOXL 配置"""
        config = get_soxl_config()

        assert "SOXL" in config.trading.symbols
        assert config.trading.max_position_pct == 0.2  # 更保守
        assert config.risk.daily_loss_limit == 0.02  # 更严格

    def test_aapl_config(self):
        """测试 AAPL 配置"""
        config = get_aapl_config()

        assert config.trading.symbols == ["AAPL"]
        assert config.trading.max_position_pct == 0.5
        assert config.risk.max_slippage == 0.001  # 大盘股滑点更小

    def test_options_config(self):
        """测试期权配置"""
        config = get_options_config()

        assert config.trading.max_position_pct == 0.1
        assert config.risk.daily_loss_limit == 0.02
        assert config.risk.max_drawdown == 0.10

    def test_multi_stock_config(self):
        """测试多标的配置"""
        symbols = ["AAPL", "MSFT", "GOOGL", "AMZN"]
        config = get_multi_stock_config(symbols)

        assert config.trading.symbols == symbols
        # 仓位应该是均分的
        assert config.trading.max_position_pct <= 0.25


class TestGetConfig:
    """配置获取测试"""

    def test_get_known_config(self):
        """测试获取已知配置"""
        config = get_config("tqqq_qqq")

        assert config is not None
        assert "TQQQ" in config.trading.symbols

    def test_get_unknown_config(self):
        """测试获取未知配置"""
        config = get_config("unknown_config")

        # 应该返回默认配置
        assert config is not None
        assert isinstance(config, HFTConfig)


class TestConfigRegistry:
    """配置注册表测试"""

    def test_registry_contains_all_configs(self):
        """测试注册表包含所有配置"""
        expected = ["tqqq_qqq", "spxl", "soxl", "aapl", "options"]

        for name in expected:
            assert name in CONFIG_REGISTRY

    def test_all_registry_configs_work(self):
        """测试所有注册的配置都能正常工作"""
        for name, factory in CONFIG_REGISTRY.items():
            config = factory()

            assert config is not None
            assert isinstance(config, HFTConfig)
            assert len(config.trading.symbols) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
