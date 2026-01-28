# -*- coding: utf-8 -*-
"""
高频交易系统集成测试
"""

import pytest
import asyncio
import json
import time
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestHighFrequencyTrader:
    """高频交易器集成测试"""

    @pytest.fixture
    def trader_config(self, tmp_path):
        """创建测试配置"""
        config = {
            "trading": {
                "initial_cash": 50000.0,
                "max_position_per_symbol": 0.20,
                "trading_interval": 1,
                "enable_premarket": True,
                "enable_afterhours": True
            },
            "risk": {
                "daily_loss_limit": 0.03,
                "max_drawdown": 0.15,
                "max_slippage": 0.002,
                "auto_circuit_breaker": True
            },
            "performance": {
                "target_loop_time_ms": 1000,
                "target_order_latency_ms": 1.4
            },
            "monitoring": {
                "metrics_port": 19091,
                "enable_feishu": False,
                "feishu_webhook": ""
            },
            "model": {
                "name": "test-model",
                "base_url": "http://test",
                "api_key": "test-key"
            }
        }

        config_path = tmp_path / "test_config.json"
        with open(config_path, "w") as f:
            json.dump(config, f)

        return str(config_path)

    @pytest.mark.asyncio
    async def test_trader_initialization(self, trader_config):
        """测试交易器初始化"""
        from main_hft import HighFrequencyTrader

        trader = HighFrequencyTrader(
            symbols=["TQQQ", "QQQ"],
            config_path=trader_config,
            dry_run=True
        )

        assert trader.symbols == ["TQQQ", "QQQ"]
        assert trader.dry_run == True
        assert trader.config is not None

    @pytest.mark.asyncio
    async def test_trader_full_initialize(self, trader_config):
        """测试完整初始化"""
        from main_hft import HighFrequencyTrader

        trader = HighFrequencyTrader(
            symbols=["TQQQ"],
            config_path=trader_config,
            dry_run=True
        )

        await trader.initialize()

        assert trader._executor is not None
        assert trader._subscriber is not None
        assert trader._risk_manager is not None
        assert trader._metrics_exporter is not None

        await trader.stop()

    @pytest.mark.asyncio
    async def test_get_market_data(self, trader_config):
        """测试获取市场数据"""
        from main_hft import HighFrequencyTrader

        trader = HighFrequencyTrader(
            symbols=["TQQQ"],
            config_path=trader_config,
            dry_run=True
        )

        await trader.initialize()

        market_data = await trader.get_market_data("TQQQ")

        assert market_data is not None
        assert "current_price" in market_data
        assert "klines" in market_data

        await trader.stop()

    @pytest.mark.asyncio
    async def test_make_decision(self, trader_config):
        """测试决策"""
        from main_hft import HighFrequencyTrader

        trader = HighFrequencyTrader(
            symbols=["TQQQ"],
            config_path=trader_config,
            dry_run=True
        )

        await trader.initialize()

        market_data = await trader.get_market_data("TQQQ")
        decision = await trader.make_decision(market_data)

        assert decision is not None
        assert "action" in decision
        assert decision["action"] in ["long", "short", "flat", "hold"]

        await trader.stop()

    @pytest.mark.asyncio
    async def test_execute_decision_dry_run(self, trader_config):
        """测试执行决策（模拟模式）"""
        from main_hft import HighFrequencyTrader

        trader = HighFrequencyTrader(
            symbols=["TQQQ"],
            config_path=trader_config,
            dry_run=True
        )

        await trader.initialize()

        market_data = {"current_price": 75.0}
        decision = {"action": "long", "quantity": 10, "reason": "Test"}

        result = await trader.execute_decision("TQQQ", decision, market_data)

        assert result is not None
        assert result.get("dry_run") == True

        await trader.stop()

    @pytest.mark.asyncio
    async def test_performance_stats(self, trader_config):
        """测试性能统计"""
        from main_hft import HighFrequencyTrader

        trader = HighFrequencyTrader(
            symbols=["TQQQ"],
            config_path=trader_config,
            dry_run=True
        )

        await trader.initialize()

        # 模拟一些操作
        market_data = await trader.get_market_data("TQQQ")
        await trader.make_decision(market_data)

        stats = trader.get_performance_stats()

        assert "loop_times" in stats
        assert "decision_times" in stats
        assert "execution_times" in stats

        await trader.stop()


class TestEndToEndFlow:
    """端到端流程测试"""

    @pytest.mark.asyncio
    async def test_full_trading_cycle(self):
        """测试完整交易周期"""
        # 初始化所有组件
        from futu.opend_client import init_opend, shutdown_opend, OpenDConfig
        from futu.trade_executor import FutuTradeExecutor
        from futu.quote_subscriber import FutuQuoteSubscriber
        from risk_control.risk_manager import RiskManager, RiskConfig

        # 1. 初始化连接
        config = OpenDConfig(pool_size=1)
        init_opend(config)

        # 2. 创建执行器
        executor = FutuTradeExecutor(trd_env=1, max_slippage=0.002)

        # 3. 创建行情订阅
        subscriber = FutuQuoteSubscriber(symbols=["TQQQ"])

        # 4. 创建风控
        risk_manager = RiskManager(RiskConfig(
            daily_loss_threshold=0.03,
            max_drawdown=0.15
        ))
        risk_manager.initialize(50000.0)

        # 5. 获取行情
        quote = await subscriber.get_quote("TQQQ")
        assert quote is not None

        # 6. 风控检查
        risk_check = risk_manager.pre_trade_check(
            symbol="TQQQ",
            side="long",
            quantity=10,
            price=quote.last_price
        )
        assert risk_check.allowed == True

        # 7. 执行交易
        result = await executor.long("TQQQ", 10)
        assert result.success == True

        # 8. 交易后检查
        violation = risk_manager.post_trade_check(
            symbol="TQQQ",
            expected_price=quote.last_price,
            executed_price=result.filled_price
        )
        assert violation.slippage < 0.01  # 1%以内

        # 9. 平仓
        flat_result = await executor.flat("TQQQ")
        assert flat_result.success == True

        # 清理
        await subscriber.close()
        await executor.close()
        shutdown_opend()

    @pytest.mark.asyncio
    async def test_risk_triggered_halt(self):
        """测试风控触发停止"""
        from futu.opend_client import init_opend, shutdown_opend, OpenDConfig
        from futu.trade_executor import FutuTradeExecutor
        from risk_control.risk_manager import RiskManager, RiskConfig

        config = OpenDConfig(pool_size=1)
        init_opend(config)

        executor = FutuTradeExecutor(trd_env=1)
        risk_manager = RiskManager(RiskConfig(daily_loss_threshold=0.03))
        risk_manager.initialize(10000.0)

        # 模拟大幅亏损
        risk_manager.update_equity(9600.0)  # 4%亏损

        # 此时交易应该被阻止
        risk_check = risk_manager.pre_trade_check(
            symbol="TQQQ",
            side="long",
            quantity=10,
            price=75.0
        )

        assert risk_check.allowed == False

        await executor.close()
        shutdown_opend()


class TestPerformanceRequirements:
    """性能要求测试"""

    @pytest.mark.asyncio
    async def test_order_latency(self):
        """测试下单延迟"""
        from futu.opend_client import init_opend, shutdown_opend, OpenDConfig
        from futu.trade_executor import FutuTradeExecutor

        config = OpenDConfig(pool_size=1)
        init_opend(config)

        executor = FutuTradeExecutor(trd_env=1)

        latencies = []
        for _ in range(10):
            start = time.perf_counter()
            result = await executor.long("TQQQ", 1)
            latency = (time.perf_counter() - start) * 1000
            latencies.append(latency)

        avg_latency = sum(latencies) / len(latencies)

        # Mock 模式下延迟应该很低
        assert avg_latency < 100  # 100ms以内

        await executor.close()
        shutdown_opend()

    @pytest.mark.asyncio
    async def test_quote_latency(self):
        """测试行情延迟"""
        from futu.opend_client import init_opend, shutdown_opend, OpenDConfig
        from futu.quote_subscriber import FutuQuoteSubscriber

        config = OpenDConfig(pool_size=1)
        init_opend(config)

        subscriber = FutuQuoteSubscriber(symbols=["TQQQ"])

        latencies = []
        for _ in range(10):
            start = time.perf_counter()
            quote = await subscriber.get_quote("TQQQ", use_cache=False)
            latency = (time.perf_counter() - start) * 1000
            latencies.append(latency)

        avg_latency = sum(latencies) / len(latencies)

        # 行情获取应该很快
        assert avg_latency < 50  # 50ms以内

        await subscriber.close()
        shutdown_opend()

    @pytest.mark.asyncio
    async def test_full_cycle_latency(self):
        """测试完整周期延迟"""
        from futu.opend_client import init_opend, shutdown_opend, OpenDConfig
        from futu.trade_executor import FutuTradeExecutor
        from futu.quote_subscriber import FutuQuoteSubscriber
        from risk_control.risk_manager import RiskManager, RiskConfig

        config = OpenDConfig(pool_size=1)
        init_opend(config)

        executor = FutuTradeExecutor(trd_env=1)
        subscriber = FutuQuoteSubscriber(symbols=["TQQQ"])
        risk_manager = RiskManager()
        risk_manager.initialize(50000.0)

        latencies = []
        for _ in range(5):
            start = time.perf_counter()

            # 获取行情
            quote = await subscriber.get_quote("TQQQ")

            # 风控检查
            risk_check = risk_manager.pre_trade_check(
                "TQQQ", "long", 10, quote.last_price
            )

            # 执行交易
            if risk_check.allowed:
                result = await executor.long("TQQQ", 10)

            latency = (time.perf_counter() - start) * 1000
            latencies.append(latency)

        avg_latency = sum(latencies) / len(latencies)

        # 完整周期应该在1秒以内
        assert avg_latency < 1000

        await subscriber.close()
        await executor.close()
        shutdown_opend()


class TestMultiSymbolTrading:
    """多标的交易测试"""

    @pytest.mark.asyncio
    async def test_trade_multiple_symbols(self):
        """测试多标的交易"""
        from futu.opend_client import init_opend, shutdown_opend, OpenDConfig
        from futu.trade_executor import FutuTradeExecutor
        from futu.quote_subscriber import FutuQuoteSubscriber

        symbols = ["TQQQ", "QQQ", "SOXL", "SPXL"]

        config = OpenDConfig(pool_size=2)
        init_opend(config)

        executor = FutuTradeExecutor(trd_env=1)
        subscriber = FutuQuoteSubscriber(symbols=symbols)

        results = {}
        for symbol in symbols:
            quote = await subscriber.get_quote(symbol)
            result = await executor.long(symbol, 10)
            results[symbol] = {
                "quote": quote.to_dict() if quote else None,
                "order": result.to_dict()
            }

        # 验证所有订单都成功
        for symbol, data in results.items():
            assert data["order"]["success"] == True

        await subscriber.close()
        await executor.close()
        shutdown_opend()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
