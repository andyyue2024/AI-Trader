# -*- coding: utf-8 -*-
"""
交易时段管理器
支持盘前、正常交易、盘后、夜盘无缝接力
美股交易时段 (Eastern Time):
- 盘前: 04:00 - 09:30
- 正常: 09:30 - 16:00
- 盘后: 16:00 - 20:00
"""

import logging
from dataclasses import dataclass
from datetime import datetime, time, timedelta, date
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
import threading

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MarketSession(Enum):
    """交易时段"""
    PRE_MARKET = "pre_market"       # 盘前 04:00-09:30 ET
    REGULAR = "regular"              # 正常 09:30-16:00 ET
    AFTER_HOURS = "after_hours"     # 盘后 16:00-20:00 ET
    OVERNIGHT = "overnight"          # 夜盘/休市
    CLOSED = "closed"               # 完全休市


class MarketType(Enum):
    """市场类型"""
    US_STOCK = "us_stock"           # 美股
    US_OPTIONS = "us_options"       # 美股期权
    US_FUTURES = "us_futures"       # 美股期货
    HK_STOCK = "hk_stock"           # 港股
    CN_STOCK = "cn_stock"           # A股


@dataclass
class SessionConfig:
    """时段配置"""
    session: MarketSession
    start_time: time
    end_time: time
    can_trade: bool = True
    order_types: List[str] = None  # 允许的订单类型

    def __post_init__(self):
        if self.order_types is None:
            self.order_types = ["market", "limit"]


@dataclass
class TradingCalendar:
    """交易日历"""
    # 美股节假日 (2024-2026)
    US_HOLIDAYS = [
        # 2024
        date(2024, 1, 1),   # New Year's Day
        date(2024, 1, 15),  # MLK Day
        date(2024, 2, 19),  # Presidents Day
        date(2024, 3, 29),  # Good Friday
        date(2024, 5, 27),  # Memorial Day
        date(2024, 6, 19),  # Juneteenth
        date(2024, 7, 4),   # Independence Day
        date(2024, 9, 2),   # Labor Day
        date(2024, 11, 28), # Thanksgiving
        date(2024, 12, 25), # Christmas
        # 2025
        date(2025, 1, 1),
        date(2025, 1, 20),
        date(2025, 2, 17),
        date(2025, 4, 18),
        date(2025, 5, 26),
        date(2025, 6, 19),
        date(2025, 7, 4),
        date(2025, 9, 1),
        date(2025, 11, 27),
        date(2025, 12, 25),
        # 2026
        date(2026, 1, 1),
        date(2026, 1, 19),
        date(2026, 2, 16),
        date(2026, 4, 3),
        date(2026, 5, 25),
        date(2026, 6, 19),
        date(2026, 7, 3),
        date(2026, 9, 7),
        date(2026, 11, 26),
        date(2026, 12, 25),
    ]

    # 提前收盘日 (13:00 ET)
    EARLY_CLOSE_DAYS = [
        date(2024, 7, 3),
        date(2024, 11, 29),
        date(2024, 12, 24),
        date(2025, 7, 3),
        date(2025, 11, 28),
        date(2025, 12, 24),
        date(2026, 7, 2),
        date(2026, 11, 27),
        date(2026, 12, 24),
    ]


class SessionManager:
    """
    交易时段管理器
    管理不同市场的交易时段，支持无缝接力
    """

    # 美股时段配置 (Eastern Time)
    US_SESSIONS = [
        SessionConfig(
            session=MarketSession.PRE_MARKET,
            start_time=time(4, 0),
            end_time=time(9, 30),
            can_trade=True,
            order_types=["limit"]  # 盘前只支持限价单
        ),
        SessionConfig(
            session=MarketSession.REGULAR,
            start_time=time(9, 30),
            end_time=time(16, 0),
            can_trade=True,
            order_types=["market", "limit"]
        ),
        SessionConfig(
            session=MarketSession.AFTER_HOURS,
            start_time=time(16, 0),
            end_time=time(20, 0),
            can_trade=True,
            order_types=["limit"]  # 盘后只支持限价单
        ),
    ]

    def __init__(self, market_type: MarketType = MarketType.US_STOCK):
        self.market_type = market_type
        self._sessions = self.US_SESSIONS if market_type in [
            MarketType.US_STOCK, MarketType.US_OPTIONS
        ] else []
        self._lock = threading.Lock()

    def get_eastern_time(self) -> datetime:
        """获取美东时间"""
        try:
            from datetime import timezone
            import pytz
            et = pytz.timezone('US/Eastern')
            return datetime.now(et)
        except ImportError:
            # Fallback: UTC-5 (不考虑夏令时)
            from datetime import timezone
            utc_now = datetime.now(timezone.utc)
            return utc_now - timedelta(hours=5)

    def get_current_session(self) -> MarketSession:
        """获取当前交易时段"""
        now = self.get_eastern_time()
        current_time = now.time()
        current_date = now.date()
        weekday = now.weekday()

        # 周末休市
        if weekday >= 5:
            return MarketSession.CLOSED

        # 节假日休市
        if current_date in TradingCalendar.US_HOLIDAYS:
            return MarketSession.CLOSED

        # 提前收盘日
        if current_date in TradingCalendar.EARLY_CLOSE_DAYS:
            if current_time >= time(13, 0):
                return MarketSession.CLOSED

        # 检查各时段
        for session_config in self._sessions:
            if session_config.start_time <= current_time < session_config.end_time:
                return session_config.session

        # 夜盘/休市
        if current_time < time(4, 0) or current_time >= time(20, 0):
            return MarketSession.OVERNIGHT

        return MarketSession.CLOSED

    def get_session_config(self, session: MarketSession = None) -> Optional[SessionConfig]:
        """获取时段配置"""
        if session is None:
            session = self.get_current_session()

        for config in self._sessions:
            if config.session == session:
                return config
        return None

    def can_trade(self, session: MarketSession = None) -> bool:
        """检查是否可以交易"""
        if session is None:
            session = self.get_current_session()

        config = self.get_session_config(session)
        if config:
            return config.can_trade

        return False

    def can_use_market_order(self, session: MarketSession = None) -> bool:
        """检查是否可以使用市价单"""
        if session is None:
            session = self.get_current_session()

        config = self.get_session_config(session)
        if config:
            return "market" in config.order_types

        return False

    def get_time_to_next_session(self) -> Tuple[MarketSession, timedelta]:
        """获取到下一个交易时段的时间"""
        now = self.get_eastern_time()
        current_time = now.time()
        current_session = self.get_current_session()

        if current_session == MarketSession.CLOSED:
            # 周末
            if now.weekday() >= 5:
                days_until_monday = 7 - now.weekday()
                next_start = datetime.combine(
                    now.date() + timedelta(days=days_until_monday),
                    time(4, 0)
                )
                return MarketSession.PRE_MARKET, next_start - now.replace(tzinfo=None)

        # 找下一个时段
        for i, config in enumerate(self._sessions):
            if current_time < config.start_time:
                next_start = datetime.combine(now.date(), config.start_time)
                return config.session, next_start - now.replace(tzinfo=None)

        # 今天所有时段已结束，返回明天盘前
        next_date = now.date() + timedelta(days=1)
        # 跳过周末
        while next_date.weekday() >= 5 or next_date in TradingCalendar.US_HOLIDAYS:
            next_date += timedelta(days=1)

        next_start = datetime.combine(next_date, time(4, 0))
        return MarketSession.PRE_MARKET, next_start - now.replace(tzinfo=None)

    def get_session_end_time(self, session: MarketSession = None) -> Optional[datetime]:
        """获取时段结束时间"""
        if session is None:
            session = self.get_current_session()

        config = self.get_session_config(session)
        if config:
            now = self.get_eastern_time()
            return datetime.combine(now.date(), config.end_time)

        return None

    def get_time_remaining_in_session(self, session: MarketSession = None) -> Optional[timedelta]:
        """获取时段剩余时间"""
        if session is None:
            session = self.get_current_session()

        end_time = self.get_session_end_time(session)
        if end_time:
            now = self.get_eastern_time()
            return end_time - now.replace(tzinfo=None)

        return None

    def is_trading_day(self, check_date: date = None) -> bool:
        """检查是否为交易日"""
        if check_date is None:
            check_date = self.get_eastern_time().date()

        # 周末
        if check_date.weekday() >= 5:
            return False

        # 节假日
        if check_date in TradingCalendar.US_HOLIDAYS:
            return False

        return True

    def get_next_trading_day(self, from_date: date = None) -> date:
        """获取下一个交易日"""
        if from_date is None:
            from_date = self.get_eastern_time().date()

        next_date = from_date + timedelta(days=1)
        while not self.is_trading_day(next_date):
            next_date += timedelta(days=1)

        return next_date

    def get_status(self) -> Dict[str, Any]:
        """获取状态"""
        now = self.get_eastern_time()
        current_session = self.get_current_session()
        next_session, time_to_next = self.get_time_to_next_session()
        remaining = self.get_time_remaining_in_session()

        return {
            "current_time_et": now.strftime("%Y-%m-%d %H:%M:%S"),
            "current_session": current_session.value,
            "can_trade": self.can_trade(),
            "can_use_market_order": self.can_use_market_order(),
            "time_remaining": str(remaining) if remaining else None,
            "next_session": next_session.value,
            "time_to_next_session": str(time_to_next),
            "is_trading_day": self.is_trading_day(),
            "market_type": self.market_type.value
        }


# 便捷函数
_session_manager: Optional[SessionManager] = None


def get_session_manager(market_type: MarketType = MarketType.US_STOCK) -> SessionManager:
    """获取时段管理器单例"""
    global _session_manager
    if _session_manager is None or _session_manager.market_type != market_type:
        _session_manager = SessionManager(market_type)
    return _session_manager


def is_market_open() -> bool:
    """检查市场是否开放"""
    return get_session_manager().can_trade()


def get_current_session() -> MarketSession:
    """获取当前时段"""
    return get_session_manager().get_current_session()
