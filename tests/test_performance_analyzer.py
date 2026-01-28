# -*- coding: utf-8 -*-
"""
绩效分析器单元测试
"""

import pytest
import math
from datetime import datetime, date, timedelta
from unittest.mock import Mock, patch

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from risk_control.performance_analyzer import (
    PerformanceAnalyzer, PerformanceMetrics, TradeRecord, DailyStats,
    get_performance_analyzer
)


class TestTradeRecord:
    """交易记录测试"""

    def test_basic_trade(self):
        """测试基本交易记录"""
        trade = TradeRecord(
            trade_id="T001",
            symbol="TQQQ",
            side="long",
            quantity=100,
            entry_price=75.0
        )

        assert trade.symbol == "TQQQ"
        assert trade.is_closed == False
        assert trade.gross_pnl == 0.0

    def test_closed_long_trade_profit(self):
        """测试平仓多头盈利"""
        trade = TradeRecord(
            trade_id="T001",
            symbol="TQQQ",
            side="long",
            quantity=100,
            entry_price=75.0,
            exit_price=80.0,
            status="closed"
        )

        assert trade.is_closed == True
        assert trade.gross_pnl == 500.0  # (80-75)*100
        assert abs(trade.return_pct - 0.0667) < 0.001

    def test_closed_long_trade_loss(self):
        """测试平仓多头亏损"""
        trade = TradeRecord(
            trade_id="T002",
            symbol="TQQQ",
            side="long",
            quantity=100,
            entry_price=75.0,
            exit_price=70.0,
            status="closed"
        )

        assert trade.gross_pnl == -500.0

    def test_closed_short_trade_profit(self):
        """测试平仓空头盈利"""
        trade = TradeRecord(
            trade_id="T003",
            symbol="TQQQ",
            side="short",
            quantity=100,
            entry_price=75.0,
            exit_price=70.0,
            status="closed"
        )

        assert trade.gross_pnl == 500.0  # (75-70)*100

    def test_net_pnl_with_commission(self):
        """测试扣除佣金后净利润"""
        trade = TradeRecord(
            trade_id="T004",
            symbol="TQQQ",
            side="long",
            quantity=100,
            entry_price=75.0,
            exit_price=80.0,
            commission=10.0,
            status="closed"
        )

        assert trade.net_pnl == 490.0  # 500 - 10

    def test_holding_time(self):
        """测试持仓时间"""
        entry = datetime(2025, 1, 1, 10, 0, 0)
        exit_time = datetime(2025, 1, 1, 14, 30, 0)

        trade = TradeRecord(
            trade_id="T005",
            symbol="TQQQ",
            side="long",
            quantity=100,
            entry_price=75.0,
            exit_price=76.0,
            entry_time=entry,
            exit_time=exit_time,
            status="closed"
        )

        assert trade.holding_time == timedelta(hours=4, minutes=30)


class TestDailyStats:
    """每日统计测试"""

    def test_daily_return(self):
        """测试日收益率"""
        stats = DailyStats(
            date=date.today(),
            starting_equity=10000.0,
            ending_equity=10300.0,
            high_watermark=10350.0,
            low_watermark=9900.0
        )

        assert abs(stats.daily_return - 0.03) < 0.0001

    def test_drawdown(self):
        """测试日内回撤"""
        stats = DailyStats(
            date=date.today(),
            starting_equity=10000.0,
            ending_equity=10000.0,
            high_watermark=10500.0,
            low_watermark=10000.0
        )

        # (10500 - 10000) / 10500 = 0.0476
        assert abs(stats.drawdown - 0.0476) < 0.001

    def test_win_rate(self):
        """测试胜率"""
        stats = DailyStats(
            date=date.today(),
            starting_equity=10000.0,
            ending_equity=10100.0,
            high_watermark=10100.0,
            low_watermark=10000.0,
            trade_count=10,
            win_count=6,
            loss_count=4
        )

        assert stats.win_rate == 0.6


class TestPerformanceAnalyzer:
    """绩效分析器测试"""

    @pytest.fixture
    def analyzer(self):
        """创建分析器"""
        return PerformanceAnalyzer(initial_equity=50000.0)

    def test_initialization(self, analyzer):
        """测试初始化"""
        assert analyzer.initial_equity == 50000.0
        assert analyzer.current_equity == 50000.0

    def test_record_trade(self, analyzer):
        """测试记录交易"""
        trade = TradeRecord(
            trade_id="T001",
            symbol="TQQQ",
            side="long",
            quantity=100,
            entry_price=75.0,
            exit_price=80.0,
            status="closed"
        )

        analyzer.record_trade(trade)

        assert analyzer.current_equity == 50500.0  # 50000 + 500
        assert len(analyzer._trades) == 1

    def test_record_order(self, analyzer):
        """测试记录订单"""
        analyzer.record_order(submitted=True, filled=True, slippage=0.001)
        analyzer.record_order(submitted=True, filled=False, rejected=True)

        assert analyzer._orders_submitted == 2
        assert analyzer._orders_filled == 1
        assert analyzer._orders_rejected == 1

    def test_sharpe_ratio_calculation(self, analyzer):
        """测试夏普比率计算"""
        # 模拟一些日收益率
        returns = [0.01, 0.02, -0.005, 0.015, 0.008, -0.01, 0.02]

        sharpe = analyzer.calculate_sharpe_ratio(returns)

        # 应该是正数（平均收益为正）
        assert sharpe > 0

    def test_sharpe_ratio_negative(self, analyzer):
        """测试负收益的夏普比率"""
        returns = [-0.01, -0.02, -0.005, -0.015, -0.008]

        sharpe = analyzer.calculate_sharpe_ratio(returns)

        assert sharpe < 0

    def test_sortino_ratio(self, analyzer):
        """测试索提诺比率"""
        returns = [0.01, 0.02, -0.005, 0.015, 0.008, -0.01, 0.02]

        sortino = analyzer.calculate_sortino_ratio(returns)

        # 索提诺比率通常比夏普比率高（只考虑下行风险）
        sharpe = analyzer.calculate_sharpe_ratio(returns)
        assert sortino >= sharpe or abs(sortino - sharpe) < 1

    def test_max_drawdown(self, analyzer):
        """测试最大回撤计算"""
        # 模拟权益曲线
        analyzer._equity_curve = [
            (datetime(2025, 1, 1), 50000),
            (datetime(2025, 1, 2), 52000),  # 新高
            (datetime(2025, 1, 3), 50000),  # 回撤
            (datetime(2025, 1, 4), 48000),  # 更大回撤
            (datetime(2025, 1, 5), 51000),  # 反弹
        ]

        max_dd, duration = analyzer.calculate_max_drawdown()

        # (52000 - 48000) / 52000 = 0.0769
        assert abs(max_dd - 0.0769) < 0.001

    def test_volatility(self, analyzer):
        """测试波动率计算"""
        returns = [0.01, 0.02, -0.005, 0.015, 0.008, -0.01, 0.02]

        vol = analyzer.calculate_volatility(returns)

        assert vol > 0
        assert vol < 1  # 年化波动率应该在合理范围内

    def test_profit_factor(self, analyzer):
        """测试盈亏比"""
        # 添加一些交易
        winning_trade = TradeRecord(
            trade_id="T001", symbol="TQQQ", side="long",
            quantity=100, entry_price=75.0, exit_price=80.0,
            status="closed"
        )
        losing_trade = TradeRecord(
            trade_id="T002", symbol="TQQQ", side="long",
            quantity=100, entry_price=75.0, exit_price=73.0,
            status="closed"
        )

        analyzer.record_trade(winning_trade)
        analyzer.record_trade(losing_trade)

        pf = analyzer.calculate_profit_factor()

        # 500 / 200 = 2.5
        assert abs(pf - 2.5) < 0.01

    def test_get_performance_metrics(self, analyzer):
        """测试获取完整绩效指标"""
        # 添加一些交易
        for i in range(5):
            pnl = 100 if i % 2 == 0 else -50
            trade = TradeRecord(
                trade_id=f"T{i:03d}",
                symbol="TQQQ",
                side="long",
                quantity=100,
                entry_price=75.0,
                exit_price=75.0 + (pnl / 100),
                status="closed"
            )
            analyzer.record_trade(trade)

        # 记录订单
        for _ in range(10):
            analyzer.record_order(submitted=True, filled=True, slippage=0.001)

        metrics = analyzer.get_performance_metrics()

        assert metrics.total_trades == 5
        assert metrics.winning_trades == 3
        assert metrics.losing_trades == 2
        assert metrics.fill_rate == 1.0  # 100% 成交率

    def test_meets_targets(self, analyzer):
        """测试目标达成检查"""
        metrics = PerformanceMetrics(
            sharpe_ratio=2.5,
            max_drawdown=0.10,
            avg_daily_volume=60000,
            fill_rate=0.98
        )

        targets = metrics.meets_targets()

        assert targets["sharpe_ratio"] == True
        assert targets["max_drawdown"] == True
        assert targets["daily_volume"] == True
        assert targets["fill_rate"] == True

    def test_fails_targets(self, analyzer):
        """测试目标未达成"""
        metrics = PerformanceMetrics(
            sharpe_ratio=1.5,  # < 2
            max_drawdown=0.20,  # > 15%
            avg_daily_volume=30000,  # < 50000
            fill_rate=0.90  # < 95%
        )

        targets = metrics.meets_targets()

        assert targets["sharpe_ratio"] == False
        assert targets["max_drawdown"] == False
        assert targets["daily_volume"] == False
        assert targets["fill_rate"] == False

    def test_reset(self, analyzer):
        """测试重置"""
        # 添加一些数据
        trade = TradeRecord(
            trade_id="T001", symbol="TQQQ", side="long",
            quantity=100, entry_price=75.0, exit_price=80.0,
            status="closed"
        )
        analyzer.record_trade(trade)
        analyzer.record_order(submitted=True, filled=True)

        # 重置
        analyzer.reset(initial_equity=100000.0)

        assert analyzer.initial_equity == 100000.0
        assert analyzer.current_equity == 100000.0
        assert len(analyzer._trades) == 0
        assert analyzer._orders_submitted == 0


class TestGlobalAnalyzer:
    """全局分析器测试"""

    def test_get_performance_analyzer(self):
        """测试获取单例"""
        analyzer1 = get_performance_analyzer(50000.0)
        analyzer2 = get_performance_analyzer(100000.0)  # 应该返回同一个

        assert analyzer1 is analyzer2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
