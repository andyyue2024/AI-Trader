# -*- coding: utf-8 -*-
"""
熔断器
实现日内3%自动熔断机制
"""

import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, date
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CircuitBreakerState(Enum):
    """熔断器状态"""
    CLOSED = "closed"           # 正常状态，允许交易
    OPEN = "open"               # 熔断状态，禁止交易
    HALF_OPEN = "half_open"     # 半开状态，允许有限交易


@dataclass
class CircuitBreakerConfig:
    """熔断器配置"""
    # 日内亏损熔断阈值
    daily_loss_threshold: float = 0.03      # 3%
    # 单笔亏损熔断阈值
    single_loss_threshold: float = 0.01     # 1%
    # 连续亏损次数熔断
    consecutive_loss_count: int = 5
    # 熔断恢复时间（秒）
    recovery_time: float = 300              # 5分钟
    # 半开状态允许的订单数
    half_open_order_limit: int = 1
    # 自动恢复
    auto_recover: bool = True


@dataclass
class TradingStats:
    """交易统计"""
    date: date = field(default_factory=date.today)
    initial_equity: float = 0.0
    current_equity: float = 0.0
    high_watermark: float = 0.0
    total_pnl: float = 0.0
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0
    trade_count: int = 0
    win_count: int = 0
    loss_count: int = 0
    consecutive_losses: int = 0

    @property
    def daily_return(self) -> float:
        """日内收益率"""
        if self.initial_equity > 0:
            return (self.current_equity - self.initial_equity) / self.initial_equity
        return 0.0

    @property
    def drawdown(self) -> float:
        """当前回撤"""
        if self.high_watermark > 0:
            return (self.high_watermark - self.current_equity) / self.high_watermark
        return 0.0

    @property
    def win_rate(self) -> float:
        """胜率"""
        if self.trade_count > 0:
            return self.win_count / self.trade_count
        return 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "date": self.date.isoformat(),
            "initial_equity": self.initial_equity,
            "current_equity": self.current_equity,
            "high_watermark": self.high_watermark,
            "total_pnl": round(self.total_pnl, 2),
            "daily_return": round(self.daily_return, 4),
            "drawdown": round(self.drawdown, 4),
            "trade_count": self.trade_count,
            "win_rate": round(self.win_rate, 4),
            "consecutive_losses": self.consecutive_losses
        }


class CircuitBreaker:
    """
    熔断器
    实现日内3%自动熔断机制
    """

    def __init__(self, config: Optional[CircuitBreakerConfig] = None):
        self.config = config or CircuitBreakerConfig()
        self._state = CircuitBreakerState.CLOSED
        self._stats = TradingStats()
        self._tripped_time: Optional[datetime] = None
        self._half_open_orders = 0
        self._lock = threading.Lock()
        self._callbacks: Dict[str, List[Callable]] = {}

        # 熔断原因
        self._trip_reason: Optional[str] = None

    def initialize(self, initial_equity: float):
        """初始化每日统计"""
        with self._lock:
            self._stats = TradingStats(
                date=date.today(),
                initial_equity=initial_equity,
                current_equity=initial_equity,
                high_watermark=initial_equity
            )
            self._state = CircuitBreakerState.CLOSED
            self._tripped_time = None
            self._trip_reason = None
            self._half_open_orders = 0

        logger.info(f"Circuit breaker initialized with equity: ${initial_equity:,.2f}")

    def update_equity(self, current_equity: float, trade_pnl: Optional[float] = None):
        """更新权益和统计"""
        with self._lock:
            # 检查日期是否变化
            if self._stats.date != date.today():
                self.initialize(current_equity)
                return

            old_equity = self._stats.current_equity
            self._stats.current_equity = current_equity

            # 更新高水位
            if current_equity > self._stats.high_watermark:
                self._stats.high_watermark = current_equity

            # 更新总PnL
            self._stats.total_pnl = current_equity - self._stats.initial_equity

            # 如果有交易PnL
            if trade_pnl is not None:
                self._stats.trade_count += 1
                self._stats.realized_pnl += trade_pnl

                if trade_pnl > 0:
                    self._stats.win_count += 1
                    self._stats.consecutive_losses = 0
                elif trade_pnl < 0:
                    self._stats.loss_count += 1
                    self._stats.consecutive_losses += 1

            self._stats.unrealized_pnl = self._stats.total_pnl - self._stats.realized_pnl

        # 检查是否触发熔断
        self._check_triggers()

    def _check_triggers(self):
        """检查熔断触发条件"""
        if self._state == CircuitBreakerState.OPEN:
            # 已熔断，检查是否恢复
            if self.config.auto_recover:
                self._check_recovery()
            return

        # 检查日内亏损
        if self._stats.daily_return <= -self.config.daily_loss_threshold:
            self._trip(f"Daily loss exceeded {self.config.daily_loss_threshold:.1%}: "
                      f"{self._stats.daily_return:.2%}")
            return

        # 检查连续亏损
        if self._stats.consecutive_losses >= self.config.consecutive_loss_count:
            self._trip(f"Consecutive losses: {self._stats.consecutive_losses}")
            return

    def _trip(self, reason: str):
        """触发熔断"""
        with self._lock:
            self._state = CircuitBreakerState.OPEN
            self._tripped_time = datetime.now()
            self._trip_reason = reason

        logger.warning(f"⚠️ Circuit breaker TRIPPED: {reason}")
        self._notify("on_trip", reason, self._stats)

    def _check_recovery(self):
        """检查是否可以恢复"""
        if self._tripped_time is None:
            return

        elapsed = (datetime.now() - self._tripped_time).total_seconds()

        if elapsed >= self.config.recovery_time:
            if self._state == CircuitBreakerState.OPEN:
                # 进入半开状态
                with self._lock:
                    self._state = CircuitBreakerState.HALF_OPEN
                    self._half_open_orders = 0
                logger.info("Circuit breaker entering HALF_OPEN state")
                self._notify("on_half_open")

    def can_trade(self) -> bool:
        """检查是否允许交易"""
        self._check_recovery()

        with self._lock:
            if self._state == CircuitBreakerState.CLOSED:
                return True

            if self._state == CircuitBreakerState.HALF_OPEN:
                if self._half_open_orders < self.config.half_open_order_limit:
                    self._half_open_orders += 1
                    return True
                return False

            return False  # OPEN state

    def record_half_open_result(self, success: bool):
        """记录半开状态交易结果"""
        with self._lock:
            if self._state != CircuitBreakerState.HALF_OPEN:
                return

            if success:
                self._state = CircuitBreakerState.CLOSED
                self._tripped_time = None
                self._trip_reason = None
                logger.info("Circuit breaker RECOVERED to CLOSED state")
                self._notify("on_recover")
            else:
                self._state = CircuitBreakerState.OPEN
                self._tripped_time = datetime.now()
                logger.warning("Circuit breaker back to OPEN state after failed trade")

    def force_trip(self, reason: str = "Manual trigger"):
        """手动触发熔断"""
        self._trip(reason)

    def force_recover(self):
        """手动恢复"""
        with self._lock:
            self._state = CircuitBreakerState.CLOSED
            self._tripped_time = None
            self._trip_reason = None
        logger.info("Circuit breaker manually RECOVERED")
        self._notify("on_recover")

    def register_callback(self, event: str, callback: Callable):
        """注册事件回调"""
        if event not in self._callbacks:
            self._callbacks[event] = []
        self._callbacks[event].append(callback)

    def _notify(self, event: str, *args):
        """通知回调"""
        for cb in self._callbacks.get(event, []):
            try:
                cb(*args)
            except Exception as e:
                logger.error(f"Callback error: {e}")

    @property
    def state(self) -> CircuitBreakerState:
        return self._state

    @property
    def stats(self) -> TradingStats:
        return self._stats

    @property
    def trip_reason(self) -> Optional[str]:
        return self._trip_reason

    def get_status(self) -> Dict[str, Any]:
        """获取熔断器状态"""
        return {
            "state": self._state.value,
            "trip_reason": self._trip_reason,
            "tripped_time": self._tripped_time.isoformat() if self._tripped_time else None,
            "time_to_recovery": max(0, self.config.recovery_time -
                ((datetime.now() - self._tripped_time).total_seconds()
                 if self._tripped_time else 0)),
            "can_trade": self.can_trade(),
            "stats": self._stats.to_dict(),
            "config": {
                "daily_loss_threshold": self.config.daily_loss_threshold,
                "single_loss_threshold": self.config.single_loss_threshold,
                "consecutive_loss_count": self.config.consecutive_loss_count,
                "recovery_time": self.config.recovery_time
            }
        }
