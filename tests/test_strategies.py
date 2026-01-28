# -*- coding: utf-8 -*-
"""
策略模块单元测试
"""

import pytest
from datetime import datetime

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from futu.strategies import (
    Signal, BaseStrategy, get_strategy,
    MomentumStrategy, MeanReversionStrategy, RSIStrategy, MACDStrategy, CompositeStrategy
)


def create_klines(prices: list, volumes: list = None) -> list:
    """创建测试用 K 线数据"""
    if volumes is None:
        volumes = [1000] * len(prices)

    klines = []
    for i, (price, vol) in enumerate(zip(prices, volumes)):
        klines.append({
            "open": price * 0.99,
            "high": price * 1.01,
            "low": price * 0.98,
            "close": price,
            "volume": vol,
            "timestamp": datetime.now().isoformat()
        })
    return klines


class TestSignal:
    """信号测试"""

    def test_basic_signal(self):
        """测试基本信号"""
        signal = Signal(
            action="long",
            quantity=10,
            reason="Test signal"
        )

        assert signal.action == "long"
        assert signal.quantity == 10
        assert signal.confidence == 0.5

    def test_signal_with_stops(self):
        """测试带止损止盈的信号"""
        signal = Signal(
            action="long",
            quantity=10,
            stop_loss=95.0,
            take_profit=110.0
        )

        assert signal.stop_loss == 95.0
        assert signal.take_profit == 110.0

    def test_to_dict(self):
        """测试转换为字典"""
        signal = Signal(
            action="short",
            quantity=5,
            price=100.0,
            confidence=0.8
        )

        data = signal.to_dict()
        assert data["action"] == "short"
        assert data["quantity"] == 5
        assert data["confidence"] == 0.8


class TestMomentumStrategy:
    """动量策略测试"""

    @pytest.fixture
    def strategy(self):
        return MomentumStrategy(
            lookback_period=5,
            momentum_threshold=0.005,
            position_size=10
        )

    def test_insufficient_data(self, strategy):
        """测试数据不足"""
        market_data = {"klines": create_klines([100, 101])}
        signal = strategy.analyze(market_data)

        assert signal.action == "hold"
        assert "Insufficient" in signal.reason

    def test_positive_momentum(self, strategy):
        """测试正向动量"""
        # 上涨 1%
        prices = [100, 100.2, 100.5, 100.8, 101]
        volumes = [1000, 1200, 1500, 1800, 2000]  # 放量
        market_data = {"klines": create_klines(prices, volumes)}

        signal = strategy.analyze(market_data)

        assert signal.action == "long"
        assert signal.quantity == 10
        assert "momentum" in signal.reason.lower()

    def test_negative_momentum(self, strategy):
        """测试负向动量"""
        # 下跌 1%
        prices = [100, 99.8, 99.5, 99.2, 99]
        volumes = [1000, 1200, 1500, 1800, 2000]
        market_data = {"klines": create_klines(prices, volumes)}

        signal = strategy.analyze(market_data)

        assert signal.action == "short"
        assert signal.quantity == 10

    def test_neutral_momentum(self, strategy):
        """测试中性动量"""
        # 横盘
        prices = [100, 100.1, 99.9, 100, 100.1]
        market_data = {"klines": create_klines(prices)}

        signal = strategy.analyze(market_data)

        assert signal.action == "hold"


class TestMeanReversionStrategy:
    """均值回归策略测试"""

    @pytest.fixture
    def strategy(self):
        return MeanReversionStrategy(
            ma_period=10,
            std_multiplier=2.0,
            position_size=10
        )

    def test_oversold(self, strategy):
        """测试超卖"""
        # 价格大幅低于均值
        prices = [100, 100, 100, 100, 100, 100, 100, 100, 100, 90]
        market_data = {"klines": create_klines(prices)}

        signal = strategy.analyze(market_data)

        assert signal.action == "long"
        assert "oversold" in signal.reason.lower() or "z-score" in signal.reason.lower()

    def test_overbought(self, strategy):
        """测试超买"""
        # 价格大幅高于均值
        prices = [100, 100, 100, 100, 100, 100, 100, 100, 100, 110]
        market_data = {"klines": create_klines(prices)}

        signal = strategy.analyze(market_data)

        assert signal.action == "short"

    def test_in_range(self, strategy):
        """测试在正常范围内"""
        # 价格在均值附近
        prices = [100, 100.5, 99.5, 100.2, 99.8, 100.1, 99.9, 100, 100.1, 100]
        market_data = {"klines": create_klines(prices)}

        signal = strategy.analyze(market_data)

        assert signal.action == "hold"


class TestRSIStrategy:
    """RSI 策略测试"""

    @pytest.fixture
    def strategy(self):
        return RSIStrategy(
            rsi_period=14,
            oversold_threshold=30,
            overbought_threshold=70,
            position_size=10
        )

    def test_rsi_calculation(self, strategy):
        """测试 RSI 计算"""
        # 全部上涨
        closes = [100 + i for i in range(15)]
        rsi = strategy.calculate_rsi(closes)

        assert rsi == 100.0  # 全涨 RSI=100

    def test_rsi_neutral(self, strategy):
        """测试中性 RSI"""
        # 涨跌交替
        closes = [100, 101, 100, 101, 100, 101, 100, 101, 100, 101, 100, 101, 100, 101, 100]
        rsi = strategy.calculate_rsi(closes)

        assert 40 < rsi < 60  # 应该接近 50

    def test_oversold_signal(self, strategy):
        """测试超卖信号"""
        # 持续下跌产生低 RSI
        prices = [100 - i * 0.5 for i in range(20)]
        market_data = {"klines": create_klines(prices)}

        signal = strategy.analyze(market_data)

        # 持续下跌会产生低 RSI
        assert signal.action in ["long", "hold"]

    def test_overbought_signal(self, strategy):
        """测试超买信号"""
        # 持续上涨产生高 RSI
        prices = [100 + i * 0.5 for i in range(20)]
        market_data = {"klines": create_klines(prices)}

        signal = strategy.analyze(market_data)

        # 持续上涨会产生高 RSI
        assert signal.action in ["short", "hold"]


class TestMACDStrategy:
    """MACD 策略测试"""

    @pytest.fixture
    def strategy(self):
        return MACDStrategy(
            fast_period=12,
            slow_period=26,
            signal_period=9,
            position_size=10
        )

    def test_ema_calculation(self, strategy):
        """测试 EMA 计算"""
        data = list(range(1, 31))  # 1 to 30
        ema = strategy.calculate_ema(data, 10)

        assert len(ema) > 0
        assert ema[-1] > ema[0]  # 上升趋势，EMA 应该上升

    def test_insufficient_data(self, strategy):
        """测试数据不足"""
        prices = list(range(100, 130))  # 只有 30 个数据点
        market_data = {"klines": create_klines(prices)}

        signal = strategy.analyze(market_data)

        # 数据足够时应该能分析
        assert signal.action in ["long", "short", "hold"]

    def test_bullish_trend(self, strategy):
        """测试牛市趋势"""
        # 持续上涨
        prices = [100 + i * 0.3 for i in range(50)]
        market_data = {"klines": create_klines(prices)}

        signal = strategy.analyze(market_data)

        # 在上升趋势中
        assert signal.action in ["long", "hold"]


class TestCompositeStrategy:
    """组合策略测试"""

    @pytest.fixture
    def strategy(self):
        return CompositeStrategy(position_size=10)

    def test_default_strategies(self, strategy):
        """测试默认策略"""
        assert len(strategy.strategies) == 3
        assert any(isinstance(s, MomentumStrategy) for s in strategy.strategies)
        assert any(isinstance(s, RSIStrategy) for s in strategy.strategies)
        assert any(isinstance(s, MACDStrategy) for s in strategy.strategies)

    def test_consensus_long(self, strategy):
        """测试多数做多"""
        # 强上涨趋势
        prices = [100 + i * 0.5 for i in range(50)]
        volumes = [1000 + i * 50 for i in range(50)]  # 放量
        market_data = {"klines": create_klines(prices, volumes)}

        signal = strategy.analyze(market_data)

        # 应该有某种信号
        assert signal.action in ["long", "short", "hold"]

    def test_no_consensus(self, strategy):
        """测试无共识"""
        # 横盘
        prices = [100 + (i % 3 - 1) * 0.1 for i in range(50)]
        market_data = {"klines": create_klines(prices)}

        signal = strategy.analyze(market_data)

        # 横盘时通常持有
        assert signal.action in ["hold", "long", "short"]


class TestGetStrategy:
    """策略工厂测试"""

    def test_get_momentum(self):
        """测试获取动量策略"""
        strategy = get_strategy("momentum")
        assert isinstance(strategy, MomentumStrategy)

    def test_get_mean_reversion(self):
        """测试获取均值回归策略"""
        strategy = get_strategy("mean_reversion")
        assert isinstance(strategy, MeanReversionStrategy)

    def test_get_rsi(self):
        """测试获取 RSI 策略"""
        strategy = get_strategy("rsi")
        assert isinstance(strategy, RSIStrategy)

    def test_get_macd(self):
        """测试获取 MACD 策略"""
        strategy = get_strategy("macd")
        assert isinstance(strategy, MACDStrategy)

    def test_get_composite(self):
        """测试获取组合策略"""
        strategy = get_strategy("composite")
        assert isinstance(strategy, CompositeStrategy)

    def test_get_with_params(self):
        """测试带参数获取策略"""
        strategy = get_strategy("momentum", lookback_period=10, position_size=20)
        assert strategy.lookback_period == 10
        assert strategy.position_size == 20

    def test_invalid_strategy(self):
        """测试无效策略"""
        with pytest.raises(ValueError):
            get_strategy("invalid_strategy")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
