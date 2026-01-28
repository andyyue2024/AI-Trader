# -*- coding: utf-8 -*-
"""
交易时段管理器单元测试
"""

import pytest
from datetime import datetime, date, time, timedelta
from unittest.mock import Mock, patch

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from futu.session_manager import (
    SessionManager, MarketSession, MarketType, TradingCalendar,
    SessionConfig, is_market_open, get_current_session, get_session_manager
)


class TestMarketSession:
    """交易时段枚举测试"""

    def test_session_values(self):
        """测试时段值"""
        assert MarketSession.PRE_MARKET.value == "pre_market"
        assert MarketSession.REGULAR.value == "regular"
        assert MarketSession.AFTER_HOURS.value == "after_hours"
        assert MarketSession.CLOSED.value == "closed"


class TestSessionConfig:
    """时段配置测试"""

    def test_default_config(self):
        """测试默认配置"""
        config = SessionConfig(
            session=MarketSession.REGULAR,
            start_time=time(9, 30),
            end_time=time(16, 0)
        )

        assert config.can_trade == True
        assert "market" in config.order_types
        assert "limit" in config.order_types

    def test_premarket_config(self):
        """测试盘前配置"""
        config = SessionConfig(
            session=MarketSession.PRE_MARKET,
            start_time=time(4, 0),
            end_time=time(9, 30),
            order_types=["limit"]
        )

        assert "market" not in config.order_types
        assert "limit" in config.order_types


class TestTradingCalendar:
    """交易日历测试"""

    def test_us_holidays(self):
        """测试美股节假日"""
        holidays = TradingCalendar.US_HOLIDAYS

        # 检查一些已知节假日
        assert date(2025, 1, 1) in holidays  # New Year's Day
        assert date(2025, 7, 4) in holidays  # Independence Day
        assert date(2025, 12, 25) in holidays  # Christmas

    def test_early_close_days(self):
        """测试提前收盘日"""
        early_close = TradingCalendar.EARLY_CLOSE_DAYS

        assert date(2025, 12, 24) in early_close  # Christmas Eve


class TestSessionManager:
    """时段管理器测试"""

    @pytest.fixture
    def manager(self):
        """创建管理器"""
        return SessionManager(MarketType.US_STOCK)

    def test_initialization(self, manager):
        """测试初始化"""
        assert manager.market_type == MarketType.US_STOCK
        assert len(manager._sessions) == 3

    def test_is_trading_day_weekday(self, manager):
        """测试工作日是否为交易日"""
        # 找一个工作日（非节假日）
        test_date = date(2025, 1, 6)  # Monday
        assert manager.is_trading_day(test_date) == True

    def test_is_trading_day_weekend(self, manager):
        """测试周末非交易日"""
        saturday = date(2025, 1, 4)
        sunday = date(2025, 1, 5)

        assert manager.is_trading_day(saturday) == False
        assert manager.is_trading_day(sunday) == False

    def test_is_trading_day_holiday(self, manager):
        """测试节假日非交易日"""
        christmas = date(2025, 12, 25)
        assert manager.is_trading_day(christmas) == False

    def test_get_next_trading_day(self, manager):
        """测试获取下一交易日"""
        # 从周五开始
        friday = date(2025, 1, 3)
        next_day = manager.get_next_trading_day(friday)

        # 下一交易日应该是周一
        assert next_day == date(2025, 1, 6)

    def test_get_session_config(self, manager):
        """测试获取时段配置"""
        config = manager.get_session_config(MarketSession.REGULAR)

        assert config is not None
        assert config.start_time == time(9, 30)
        assert config.end_time == time(16, 0)

    def test_can_trade_regular(self, manager):
        """测试正常时段可交易"""
        can = manager.can_trade(MarketSession.REGULAR)
        assert can == True

    def test_can_use_market_order_regular(self, manager):
        """测试正常时段可用市价单"""
        can = manager.can_use_market_order(MarketSession.REGULAR)
        assert can == True

    def test_can_use_market_order_premarket(self, manager):
        """测试盘前不可用市价单"""
        can = manager.can_use_market_order(MarketSession.PRE_MARKET)
        assert can == False

    def test_get_status(self, manager):
        """测试获取状态"""
        status = manager.get_status()

        assert "current_session" in status
        assert "can_trade" in status
        assert "is_trading_day" in status
        assert "market_type" in status

    @patch.object(SessionManager, 'get_eastern_time')
    def test_get_current_session_premarket(self, mock_time, manager):
        """测试盘前时段识别"""
        # 模拟美东时间 6:00 AM (盘前)
        mock_time.return_value = datetime(2025, 1, 6, 6, 0, 0)

        session = manager.get_current_session()
        assert session == MarketSession.PRE_MARKET

    @patch.object(SessionManager, 'get_eastern_time')
    def test_get_current_session_regular(self, mock_time, manager):
        """测试正常时段识别"""
        # 模拟美东时间 10:30 AM
        mock_time.return_value = datetime(2025, 1, 6, 10, 30, 0)

        session = manager.get_current_session()
        assert session == MarketSession.REGULAR

    @patch.object(SessionManager, 'get_eastern_time')
    def test_get_current_session_afterhours(self, mock_time, manager):
        """测试盘后时段识别"""
        # 模拟美东时间 5:00 PM
        mock_time.return_value = datetime(2025, 1, 6, 17, 0, 0)

        session = manager.get_current_session()
        assert session == MarketSession.AFTER_HOURS

    @patch.object(SessionManager, 'get_eastern_time')
    def test_get_current_session_weekend(self, mock_time, manager):
        """测试周末休市"""
        # 模拟周六
        mock_time.return_value = datetime(2025, 1, 4, 10, 0, 0)

        session = manager.get_current_session()
        assert session == MarketSession.CLOSED

    @patch.object(SessionManager, 'get_eastern_time')
    def test_time_remaining_in_session(self, mock_time, manager):
        """测试时段剩余时间"""
        # 模拟 3:00 PM (还有1小时到收盘)
        mock_time.return_value = datetime(2025, 1, 6, 15, 0, 0)

        remaining = manager.get_time_remaining_in_session(MarketSession.REGULAR)

        assert remaining is not None
        assert remaining.total_seconds() == 3600  # 1小时


class TestGlobalFunctions:
    """全局函数测试"""

    def test_get_session_manager(self):
        """测试获取管理器"""
        manager = get_session_manager(MarketType.US_STOCK)
        assert manager is not None
        assert manager.market_type == MarketType.US_STOCK

    def test_is_market_open(self):
        """测试市场是否开放"""
        result = is_market_open()
        assert isinstance(result, bool)

    def test_get_current_session(self):
        """测试获取当前时段"""
        session = get_current_session()
        assert isinstance(session, MarketSession)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
