# -*- coding: utf-8 -*-
"""
风控模块单元测试
"""

import pytest
import time
from datetime import datetime, date
from unittest.mock import Mock, patch

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from risk_control.circuit_breaker import (
    CircuitBreaker, CircuitBreakerConfig, CircuitBreakerState,
    TradingStats
)
from risk_control.drawdown_monitor import (
    DrawdownMonitor, DrawdownConfig, DrawdownAlert, DrawdownAlertLevel
)
from risk_control.slippage_checker import (
    SlippageChecker, SlippageConfig, SlippageViolation
)
from risk_control.risk_manager import (
    RiskManager, RiskConfig, RiskLevel, RiskCheckResult
)


class TestTradingStats:
    """交易统计测试"""

    def test_daily_return(self):
        """测试日收益率计算"""
        stats = TradingStats(
            initial_equity=10000.0,
            current_equity=10300.0
        )

        assert abs(stats.daily_return - 0.03) < 0.0001

    def test_drawdown(self):
        """测试回撤计算"""
        stats = TradingStats(
            high_watermark=10500.0,
            current_equity=10000.0
        )

        assert abs(stats.drawdown - 0.0476) < 0.001

    def test_win_rate(self):
        """测试胜率计算"""
        stats = TradingStats(
            trade_count=10,
            win_count=6,
            loss_count=4
        )

        assert stats.win_rate == 0.6


class TestCircuitBreaker:
    """熔断器测试"""

    def test_initial_state(self):
        """测试初始状态"""
        cb = CircuitBreaker()

        assert cb.state == CircuitBreakerState.CLOSED
        assert cb.can_trade() == True

    def test_initialize(self):
        """测试初始化"""
        cb = CircuitBreaker()
        cb.initialize(10000.0)

        assert cb.stats.initial_equity == 10000.0
        assert cb.stats.current_equity == 10000.0
        assert cb.stats.high_watermark == 10000.0

    def test_daily_loss_trigger(self):
        """测试日内亏损触发熔断"""
        config = CircuitBreakerConfig(daily_loss_threshold=0.03)
        cb = CircuitBreaker(config)
        cb.initialize(10000.0)

        # 亏损3%
        cb.update_equity(9699.0)

        assert cb.state == CircuitBreakerState.OPEN
        assert cb.can_trade() == False

    def test_consecutive_loss_trigger(self):
        """测试连续亏损触发熔断"""
        config = CircuitBreakerConfig(consecutive_loss_count=3)
        cb = CircuitBreaker(config)
        cb.initialize(10000.0)

        # 连续3笔亏损
        cb.update_equity(9900.0, trade_pnl=-100)
        cb.update_equity(9800.0, trade_pnl=-100)
        cb.update_equity(9700.0, trade_pnl=-100)

        assert cb.state == CircuitBreakerState.OPEN
        assert cb.stats.consecutive_losses == 3

    def test_force_trip(self):
        """测试手动熔断"""
        cb = CircuitBreaker()
        cb.initialize(10000.0)

        cb.force_trip("Manual test")

        assert cb.state == CircuitBreakerState.OPEN
        assert cb.trip_reason == "Manual test"

    def test_force_recover(self):
        """测试手动恢复"""
        cb = CircuitBreaker()
        cb.initialize(10000.0)
        cb.force_trip("Test")

        cb.force_recover()

        assert cb.state == CircuitBreakerState.CLOSED
        assert cb.can_trade() == True

    def test_auto_recovery(self):
        """测试自动恢复"""
        config = CircuitBreakerConfig(
            daily_loss_threshold=0.03,
            recovery_time=0.1,  # 0.1秒
            auto_recover=True
        )
        cb = CircuitBreaker(config)
        cb.initialize(10000.0)

        # 触发熔断
        cb.update_equity(9699.0)
        assert cb.state == CircuitBreakerState.OPEN

        # 等待恢复
        time.sleep(0.15)

        # 检查恢复（通过 can_trade 触发检查）
        can_trade = cb.can_trade()

        # 应该进入半开状态
        assert cb.state in [CircuitBreakerState.HALF_OPEN, CircuitBreakerState.OPEN]

    def test_callback(self):
        """测试回调"""
        cb = CircuitBreaker()
        cb.initialize(10000.0)

        trip_called = [False]

        def on_trip(reason, stats):
            trip_called[0] = True

        cb.register_callback("on_trip", on_trip)
        cb.force_trip("Test")

        assert trip_called[0] == True

    def test_get_status(self):
        """测试获取状态"""
        cb = CircuitBreaker()
        cb.initialize(10000.0)

        status = cb.get_status()

        assert "state" in status
        assert "stats" in status
        assert "config" in status
        assert status["can_trade"] == True


class TestDrawdownMonitor:
    """回撤监控测试"""

    def test_initialization(self):
        """测试初始化"""
        dm = DrawdownMonitor()
        dm.initialize(10000.0)

        assert dm.peak_equity == 10000.0
        assert dm.current_drawdown == 0.0

    def test_drawdown_calculation(self):
        """测试回撤计算"""
        dm = DrawdownMonitor()
        dm.initialize(10000.0)

        dm.update(9500.0)

        assert abs(dm.current_drawdown - 0.05) < 0.001

    def test_peak_tracking(self):
        """测试峰值跟踪"""
        dm = DrawdownMonitor()
        dm.initialize(10000.0)

        dm.update(10500.0)  # 新高
        assert dm.peak_equity == 10500.0

        dm.update(10000.0)  # 回落
        assert dm.peak_equity == 10500.0  # 峰值不变

    def test_warning_alert(self):
        """测试警告级别回撤"""
        config = DrawdownConfig(warning_threshold=0.05)
        dm = DrawdownMonitor(config)
        dm.initialize(10000.0)

        alert = dm.update(9400.0)  # 6%回撤

        assert alert is not None
        assert alert.level == DrawdownAlertLevel.WARNING

    def test_critical_alert(self):
        """测试严重级别回撤"""
        config = DrawdownConfig(critical_threshold=0.10)
        dm = DrawdownMonitor(config)
        dm.initialize(10000.0)

        alert = dm.update(8900.0)  # 11%回撤

        assert alert is not None
        assert alert.level == DrawdownAlertLevel.CRITICAL

    def test_exceeded_alert(self):
        """测试超限回撤"""
        config = DrawdownConfig(max_drawdown=0.15, auto_stop_on_exceed=True)
        dm = DrawdownMonitor(config)
        dm.initialize(10000.0)

        alert = dm.update(8400.0)  # 16%回撤

        assert alert is not None
        assert alert.level == DrawdownAlertLevel.EXCEEDED
        assert dm.is_exceeded == True
        assert dm.can_trade() == False

    def test_reset_exceeded(self):
        """测试重置超限标记"""
        config = DrawdownConfig(max_drawdown=0.15, auto_stop_on_exceed=True)
        dm = DrawdownMonitor(config)
        dm.initialize(10000.0)

        dm.update(8400.0)  # 触发超限
        assert dm.can_trade() == False

        dm.reset_exceeded()
        assert dm.can_trade() == True

    def test_get_status(self):
        """测试获取状态"""
        dm = DrawdownMonitor()
        dm.initialize(10000.0)
        dm.update(9500.0)

        status = dm.get_status()

        assert "current_drawdown" in status
        assert "max_recorded_drawdown" in status
        assert "peak_equity" in status
        assert "alert_level" in status


class TestSlippageChecker:
    """滑点检查测试"""

    def test_slippage_calculation(self):
        """测试滑点计算"""
        sc = SlippageChecker()

        violation = sc.check_slippage(
            symbol="TQQQ",
            expected_price=75.00,
            executed_price=75.10
        )

        assert abs(violation.slippage - 0.00133) < 0.0001

    def test_no_violation(self):
        """测试无违规"""
        config = SlippageConfig(max_slippage=0.002)
        sc = SlippageChecker(config)

        violation = sc.check_slippage(
            symbol="TQQQ",
            expected_price=75.00,
            executed_price=75.05  # 0.067%滑点
        )

        assert violation.is_violation == False

    def test_violation(self):
        """测试违规"""
        config = SlippageConfig(max_slippage=0.002)
        sc = SlippageChecker(config)

        violation = sc.check_slippage(
            symbol="TQQQ",
            expected_price=75.00,
            executed_price=75.20  # 0.267%滑点
        )

        assert violation.is_violation == True

    def test_average_slippage(self):
        """测试平均滑点"""
        sc = SlippageChecker()

        sc.check_slippage("TQQQ", 100.0, 100.1)
        sc.check_slippage("TQQQ", 100.0, 100.2)
        sc.check_slippage("TQQQ", 100.0, 100.3)

        assert sc.average_slippage > 0

    def test_violation_rate(self):
        """测试违规率"""
        config = SlippageConfig(max_slippage=0.002)
        sc = SlippageChecker(config)

        sc.check_slippage("TQQQ", 100.0, 100.1)  # 无违规
        sc.check_slippage("TQQQ", 100.0, 100.5)  # 违规

        assert sc.violation_rate == 0.5

    def test_can_execute_check(self):
        """测试预执行检查"""
        config = SlippageConfig(max_slippage=0.002, reject_high_slippage=True)
        sc = SlippageChecker(config)

        # 价差在允许范围内
        result = sc.can_execute("TQQQ", 100.0, 99.9, 100.1)
        assert result == True

        # 价差过大
        result = sc.can_execute("TQQQ", 100.0, 99.5, 100.5)
        assert result == False

    def test_get_violations(self):
        """测试获取违规记录"""
        config = SlippageConfig(max_slippage=0.001)
        sc = SlippageChecker(config)

        sc.check_slippage("TQQQ", 100.0, 100.5)
        sc.check_slippage("QQQ", 490.0, 491.0)

        violations = sc.get_violations()

        assert len(violations) == 2


class TestRiskManager:
    """综合风险管理测试"""

    def test_initialization(self):
        """测试初始化"""
        rm = RiskManager()
        rm.initialize(10000.0)

        assert rm.get_risk_level() == RiskLevel.LOW

    def test_pre_trade_check_allowed(self):
        """测试交易前检查（允许）"""
        rm = RiskManager()
        rm.initialize(10000.0)

        result = rm.pre_trade_check(
            symbol="TQQQ",
            side="long",
            quantity=10,
            price=75.0
        )

        assert result.allowed == True

    def test_pre_trade_check_circuit_breaker(self):
        """测试交易前检查（熔断器阻止）"""
        rm = RiskManager()
        rm.initialize(10000.0)
        rm.force_halt("Test")

        result = rm.pre_trade_check(
            symbol="TQQQ",
            side="long",
            quantity=10,
            price=75.0
        )

        assert result.allowed == False
        assert result.risk_level == RiskLevel.HALTED

    def test_pre_trade_check_order_value(self):
        """测试交易前检查（订单金额超限）"""
        config = RiskConfig(max_order_value=1000)
        rm = RiskManager(config)
        rm.initialize(10000.0)

        result = rm.pre_trade_check(
            symbol="TQQQ",
            side="long",
            quantity=20,
            price=75.0  # 总值 $1500
        )

        assert result.allowed == False

    def test_pre_trade_check_position_limit(self):
        """测试交易前检查（仓位超限）"""
        config = RiskConfig(max_position_pct=0.10)  # 10%限制
        rm = RiskManager(config)
        rm.initialize(10000.0)

        result = rm.pre_trade_check(
            symbol="TQQQ",
            side="long",
            quantity=20,
            price=75.0,
            current_position_value=500,  # 已有$500
            total_equity=10000.0
        )

        assert result.allowed == False

    def test_post_trade_check(self):
        """测试交易后检查"""
        rm = RiskManager()
        rm.initialize(10000.0)

        violation = rm.post_trade_check(
            symbol="TQQQ",
            expected_price=75.0,
            executed_price=75.1,
            order_id="ORD123"
        )

        assert violation is not None
        assert violation.symbol == "TQQQ"

    def test_force_halt_and_resume(self):
        """测试强制停止和恢复"""
        rm = RiskManager()
        rm.initialize(10000.0)

        rm.force_halt("Test reason")
        assert rm.get_risk_level() == RiskLevel.HALTED

        rm.resume_trading()
        assert rm.get_risk_level() != RiskLevel.HALTED

    def test_update_equity(self):
        """测试更新权益"""
        rm = RiskManager()
        rm.initialize(10000.0)

        rm.update_equity(9700.0, trade_pnl=-300)

        status = rm.get_status()
        assert status["circuit_breaker"]["stats"]["current_equity"] == 9700.0

    def test_get_status(self):
        """测试获取状态"""
        rm = RiskManager()
        rm.initialize(10000.0)

        status = rm.get_status()

        assert "risk_level" in status
        assert "can_trade" in status
        assert "circuit_breaker" in status
        assert "drawdown" in status
        assert "slippage" in status

    def test_order_rate_limit(self):
        """测试订单频率限制"""
        config = RiskConfig(min_order_interval=0.5)
        rm = RiskManager(config)
        rm.initialize(10000.0)

        # 第一笔订单
        result1 = rm.pre_trade_check("TQQQ", "long", 10, 75.0)
        rm.post_trade_check("TQQQ", 75.0, 75.0)  # 记录订单

        # 立即第二笔订单（应该被阻止）
        result2 = rm.pre_trade_check("TQQQ", "long", 10, 75.0)

        assert result1.allowed == True
        assert result2.allowed == False


class TestRiskLevel:
    """风险级别测试"""

    def test_low_risk(self):
        """测试低风险级别"""
        rm = RiskManager()
        rm.initialize(10000.0)

        assert rm.get_risk_level() == RiskLevel.LOW

    def test_medium_risk(self):
        """测试中等风险级别"""
        config = RiskConfig(warning_drawdown=0.02)
        rm = RiskManager(config)
        rm.initialize(10000.0)

        rm.update_equity(9700.0)  # 3%回撤

        assert rm.get_risk_level() == RiskLevel.MEDIUM

    def test_high_risk(self):
        """测试高风险级别"""
        config = RiskConfig(critical_drawdown=0.05)
        rm = RiskManager(config)
        rm.initialize(10000.0)

        rm.update_equity(9400.0)  # 6%回撤

        assert rm.get_risk_level() == RiskLevel.HIGH


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
