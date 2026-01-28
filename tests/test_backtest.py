# -*- coding: utf-8 -*-
"""
回测引擎单元测试
"""

import os
import pytest
import tempfile
import json
from datetime import date, datetime
from pathlib import Path

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backtest.backtest_engine import (
    BacktestConfig, BacktestEngine, BacktestResult,
    Position, Trade, run_backtest, simple_momentum_strategy
)


class TestPosition:
    """持仓测试"""

    def test_long_position(self):
        """测试多头持仓"""
        pos = Position(
            symbol="TQQQ",
            quantity=100,
            avg_cost=50.0,
            side="long"
        )

        assert pos.market_value == 5000.0
        assert pos.update_pnl(55.0) == 500.0  # 涨5块
        assert pos.update_pnl(45.0) == -500.0  # 跌5块

    def test_short_position(self):
        """测试空头持仓"""
        pos = Position(
            symbol="TQQQ",
            quantity=-100,
            avg_cost=50.0,
            side="short"
        )

        assert pos.market_value == 5000.0
        assert pos.update_pnl(45.0) == 500.0  # 空头盈利
        assert pos.update_pnl(55.0) == -500.0  # 空头亏损


class TestTrade:
    """交易测试"""

    def test_trade_to_dict(self):
        """测试交易转字典"""
        trade = Trade(
            timestamp=datetime(2024, 1, 15, 10, 30),
            symbol="TQQQ",
            side="long",
            quantity=100,
            price=50.0,
            commission=1.0,
            pnl=100.0
        )

        d = trade.to_dict()

        assert d["symbol"] == "TQQQ"
        assert d["side"] == "long"
        assert d["quantity"] == 100
        assert d["pnl"] == 100.0


class TestBacktestConfig:
    """回测配置测试"""

    def test_default_config(self):
        """测试默认配置"""
        config = BacktestConfig()

        assert config.initial_capital == 50000.0
        assert "TQQQ" in config.symbols
        assert config.commission == 0.0
        assert config.slippage == 0.001

    def test_custom_config(self):
        """测试自定义配置"""
        config = BacktestConfig(
            symbols=["AAPL", "MSFT"],
            initial_capital=100000.0,
            commission=0.001,
            slippage=0.002
        )

        assert config.initial_capital == 100000.0
        assert config.symbols == ["AAPL", "MSFT"]


class TestBacktestResult:
    """回测结果测试"""

    @pytest.fixture
    def sample_result(self):
        """创建示例结果"""
        config = BacktestConfig(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31)
        )

        result = BacktestResult(config=config)
        result.equity_curve = [
            {"date": "2024-01-01", "equity": 50000},
            {"date": "2024-06-01", "equity": 52000},
            {"date": "2024-12-31", "equity": 55000}
        ]
        result.trades = [
            Trade(datetime.now(), "TQQQ", "long", 100, 50.0, pnl=500),
            Trade(datetime.now(), "TQQQ", "flat", 100, 55.0, pnl=-200),
            Trade(datetime.now(), "QQQ", "long", 50, 400.0, pnl=300)
        ]

        return result

    def test_calculate_metrics(self, sample_result):
        """测试指标计算"""
        sample_result.calculate_metrics()

        assert sample_result.total_return == 0.1  # 10%
        assert sample_result.total_trades == 3
        assert sample_result.win_rate > 0

    def test_to_dict(self, sample_result):
        """测试转字典"""
        sample_result.calculate_metrics()
        d = sample_result.to_dict()

        assert "config" in d
        assert "metrics" in d
        assert d["metrics"]["total_return"] == 10.0


class TestBacktestEngine:
    """回测引擎测试"""

    @pytest.fixture
    def temp_data_dir(self):
        """创建临时数据目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建示例数据
            data = [
                {"date": "2024-01-02", "close": 50.0},
                {"date": "2024-01-03", "close": 51.0},
                {"date": "2024-01-04", "close": 52.0},
                {"date": "2024-01-05", "close": 51.5},
                {"date": "2024-01-08", "close": 53.0}
            ]

            for symbol in ["TQQQ", "QQQ"]:
                filepath = Path(tmpdir) / f"daily_prices_{symbol}.json"
                with open(filepath, 'w') as f:
                    json.dump(data, f)

            yield tmpdir

    @pytest.fixture
    def engine(self, temp_data_dir):
        """创建引擎"""
        config = BacktestConfig(
            symbols=["TQQQ", "QQQ"],
            data_dir=temp_data_dir,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31)
        )
        return BacktestEngine(config)

    def test_load_data(self, engine):
        """测试加载数据"""
        result = engine.load_data()

        assert result == True
        assert "TQQQ" in engine.market_data
        assert len(engine.market_data["TQQQ"]) == 5

    def test_get_price(self, engine):
        """测试获取价格"""
        engine.load_data()

        price = engine.get_price("TQQQ", "2024-01-02")
        assert price == 50.0

        price = engine.get_price("TQQQ", "2024-01-03")
        assert price == 51.0

    def test_execute_trade_long(self, engine):
        """测试执行多头交易"""
        engine.load_data()
        engine.current_date = date(2024, 1, 2)

        trade = engine.execute_trade(
            symbol="TQQQ",
            action="long",
            quantity=100,
            price=50.0,
            timestamp=datetime.now()
        )

        assert trade.side == "long"
        assert trade.quantity == 100
        assert "TQQQ" in engine.positions

    def test_execute_trade_flat(self, engine):
        """测试平仓交易"""
        engine.load_data()
        engine.current_date = date(2024, 1, 2)

        # 先开仓
        engine.execute_trade("TQQQ", "long", 100, 50.0, datetime.now())

        # 再平仓
        trade = engine.execute_trade("TQQQ", "flat", 100, 55.0, datetime.now())

        assert trade.side == "flat"
        assert "TQQQ" not in engine.positions

    def test_run_backtest(self, engine):
        """测试运行回测"""
        def test_strategy(market_data, positions):
            signals = {}
            for symbol in market_data:
                if symbol not in positions:
                    signals[symbol] = "long"
                else:
                    signals[symbol] = "hold"
            return signals

        result = engine.run(test_strategy)

        assert result is not None
        assert len(result.equity_curve) > 0


class TestConvenienceFunctions:
    """便捷函数测试"""

    def test_run_backtest_function(self):
        """测试 run_backtest 函数"""
        # 这个测试会因为没有数据而返回空结果
        result = run_backtest(
            symbols=["TEST"],
            start_date="2024-01-01",
            end_date="2024-01-31"
        )

        assert result is not None
        assert isinstance(result, BacktestResult)


class TestSimpleMomentumStrategy:
    """简单动量策略测试"""

    def test_strategy_returns_signals(self):
        """测试策略返回信号"""
        market_data = {
            "TQQQ": {"price": 50.0, "symbol": "TQQQ"},
            "QQQ": {"price": 400.0, "symbol": "QQQ"}
        }
        positions = {}

        signals = simple_momentum_strategy(market_data, positions)

        assert "TQQQ" in signals
        assert "QQQ" in signals
        assert signals["TQQQ"] == "long"

    def test_strategy_with_positions(self):
        """测试有持仓时的策略"""
        market_data = {"TQQQ": {"price": 50.0}}
        positions = {"TQQQ": Position("TQQQ", 100, 48.0, "long")}

        signals = simple_momentum_strategy(market_data, positions)

        assert signals["TQQQ"] == "hold"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
