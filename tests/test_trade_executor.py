# -*- coding: utf-8 -*-
"""
交易执行器单元测试
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from futu.trade_executor import (
    FutuTradeExecutor, OrderType, OrderSide, OrderState,
    OrderRequest, OrderResult, Position,
    quick_long, quick_short, quick_flat
)
from futu.opend_client import OpenDConfig, init_opend, shutdown_opend


@pytest.fixture
def executor():
    """创建交易执行器"""
    config = OpenDConfig(pool_size=1)
    init_opend(config)
    executor = FutuTradeExecutor(trd_env=1, max_slippage=0.002)
    yield executor
    shutdown_opend()


class TestOrderRequest:
    """订单请求测试"""

    def test_basic_request(self):
        """测试基本订单请求"""
        request = OrderRequest(
            symbol="TQQQ",
            side=OrderSide.LONG,
            quantity=100
        )

        assert request.symbol == "TQQQ"
        assert request.side == OrderSide.LONG
        assert request.quantity == 100
        assert request.order_type == OrderType.MARKET
        assert request.client_order_id is not None

    def test_limit_order(self):
        """测试限价单请求"""
        request = OrderRequest(
            symbol="QQQ",
            side=OrderSide.SHORT,
            quantity=50,
            order_type=OrderType.LIMIT,
            price=490.50
        )

        assert request.order_type == OrderType.LIMIT
        assert request.price == 490.50


class TestOrderResult:
    """订单结果测试"""

    def test_successful_result(self):
        """测试成功结果"""
        result = OrderResult(
            success=True,
            order_id="ORD123",
            symbol="TQQQ",
            side=OrderSide.LONG,
            quantity=100,
            filled_quantity=100,
            price=75.00,
            filled_price=75.02,
            state=OrderState.FILLED,
            slippage=0.00027,
            latency_ms=1.5
        )

        assert result.success == True
        assert result.state == OrderState.FILLED
        assert result.slippage < 0.002  # 滑点在限制内

    def test_to_dict(self):
        """测试转换为字典"""
        result = OrderResult(
            success=True,
            order_id="ORD123",
            symbol="TQQQ",
            side=OrderSide.LONG,
            quantity=100
        )

        data = result.to_dict()

        assert data["success"] == True
        assert data["order_id"] == "ORD123"
        assert data["side"] == "long"


class TestPosition:
    """持仓测试"""

    def test_long_position(self):
        """测试多头持仓"""
        position = Position(
            symbol="TQQQ",
            quantity=100,
            avg_cost=75.00,
            market_value=7550.00,
            unrealized_pnl=50.00
        )

        assert position.is_long == True
        assert position.is_short == False
        assert position.is_flat == False

    def test_short_position(self):
        """测试空头持仓"""
        position = Position(
            symbol="TQQQ",
            quantity=-100,
            avg_cost=75.00
        )

        assert position.is_long == False
        assert position.is_short == True
        assert position.is_flat == False

    def test_flat_position(self):
        """测试空仓"""
        position = Position(
            symbol="TQQQ",
            quantity=0,
            avg_cost=0.0
        )

        assert position.is_long == False
        assert position.is_short == False
        assert position.is_flat == True


class TestFutuTradeExecutor:
    """交易执行器测试"""

    @pytest.mark.asyncio
    async def test_long_order(self, executor):
        """测试做多订单"""
        result = await executor.long("TQQQ", 100)

        assert result.success == True
        assert result.side == OrderSide.LONG
        assert result.quantity == 100
        assert result.state == OrderState.FILLED
        assert result.latency_ms > 0

    @pytest.mark.asyncio
    async def test_short_order(self, executor):
        """测试做空订单"""
        result = await executor.short("TQQQ", 50)

        assert result.success == True
        assert result.side == OrderSide.SHORT
        assert result.quantity == 50

    @pytest.mark.asyncio
    async def test_short_disabled(self):
        """测试做空禁用"""
        config = OpenDConfig(pool_size=1)
        init_opend(config)
        executor = FutuTradeExecutor(trd_env=1, enable_short=False)

        result = await executor.short("TQQQ", 50)

        assert result.success == False
        assert result.state == OrderState.REJECTED
        assert "disabled" in result.error_message.lower()

        shutdown_opend()

    @pytest.mark.asyncio
    async def test_flat_no_position(self, executor):
        """测试无持仓时平仓"""
        result = await executor.flat("TQQQ")

        assert result.success == True
        assert result.quantity == 0

    @pytest.mark.asyncio
    async def test_get_current_price(self, executor):
        """测试获取当前价格"""
        price = await executor.get_current_price("TQQQ")

        assert price is not None
        assert price > 0

    @pytest.mark.asyncio
    async def test_get_position(self, executor):
        """测试获取持仓"""
        position = await executor.get_position("TQQQ")

        assert position is not None
        assert position.symbol == "TQQQ"

    @pytest.mark.asyncio
    async def test_slippage_calculation(self, executor):
        """测试滑点计算"""
        result = await executor.long("TQQQ", 100)

        # Mock 模式下滑点应该很小
        assert result.slippage < 0.01  # 1%以内

    @pytest.mark.asyncio
    async def test_latency_performance(self, executor):
        """测试延迟性能"""
        start = time.perf_counter()
        result = await executor.long("TQQQ", 10)
        elapsed = (time.perf_counter() - start) * 1000

        # 延迟应该在合理范围内
        assert elapsed < 1000  # 1秒以内
        assert result.latency_ms < 100  # 内部延迟100ms以内

    def test_execution_metrics(self, executor):
        """测试执行指标"""
        metrics = executor.get_execution_metrics()

        assert "total_orders" in metrics
        assert "success_rate" in metrics
        assert "average_slippage" in metrics
        assert "average_latency_ms" in metrics

    @pytest.mark.asyncio
    async def test_order_callback(self, executor):
        """测试订单回调"""
        callback_received = [None]

        def on_order(result):
            callback_received[0] = result

        executor.register_order_callback(on_order)
        await executor.long("TQQQ", 10)

        assert callback_received[0] is not None
        assert callback_received[0].success == True


class TestSymbolConversion:
    """股票代码转换测试"""

    @pytest.mark.asyncio
    async def test_us_symbol(self, executor):
        """测试美股代码转换"""
        result = await executor.long("TQQQ", 10)

        # 应该正确处理无前缀的美股代码
        assert result.symbol == "TQQQ"

    @pytest.mark.asyncio
    async def test_prefixed_symbol(self, executor):
        """测试带前缀的代码"""
        result = await executor.long("US.TQQQ", 10)

        # 应该正确处理带前缀的代码
        assert "TQQQ" in result.symbol


class TestQuickFunctions:
    """便捷函数测试"""

    @pytest.mark.asyncio
    async def test_quick_long(self):
        """测试快速做多"""
        config = OpenDConfig(pool_size=1)
        init_opend(config)

        result = await quick_long("TQQQ", 10)

        assert result.success == True
        assert result.side == OrderSide.LONG

        shutdown_opend()

    @pytest.mark.asyncio
    async def test_quick_short(self):
        """测试快速做空"""
        config = OpenDConfig(pool_size=1)
        init_opend(config)

        result = await quick_short("TQQQ", 10)

        assert result.success == True

        shutdown_opend()

    @pytest.mark.asyncio
    async def test_quick_flat(self):
        """测试快速平仓"""
        config = OpenDConfig(pool_size=1)
        init_opend(config)

        result = await quick_flat("TQQQ")

        assert result.success == True

        shutdown_opend()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
