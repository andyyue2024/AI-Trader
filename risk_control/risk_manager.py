# -*- coding: utf-8 -*-
"""
综合风险管理器
整合熔断器、回撤监控、滑点检查等风控模块
"""

import asyncio
import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from .circuit_breaker import CircuitBreaker, CircuitBreakerConfig, CircuitBreakerState
from .drawdown_monitor import DrawdownMonitor, DrawdownConfig, DrawdownAlert, DrawdownAlertLevel
from .slippage_checker import SlippageChecker, SlippageConfig, SlippageViolation

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    """风险级别"""
    LOW = "low"             # 低风险
    MEDIUM = "medium"       # 中等风险
    HIGH = "high"           # 高风险
    CRITICAL = "critical"   # 严重风险
    HALTED = "halted"       # 已停止


@dataclass
class RiskConfig:
    """综合风控配置"""
    # 熔断器配置
    daily_loss_threshold: float = 0.03      # 日内3%熔断
    single_loss_threshold: float = 0.01     # 单笔1%熔断
    consecutive_loss_count: int = 5         # 连续亏损次数
    recovery_time: float = 300              # 熔断恢复时间(秒)

    # 回撤配置
    max_drawdown: float = 0.15              # 最大回撤15%
    warning_drawdown: float = 0.05          # 警告回撤5%
    critical_drawdown: float = 0.10         # 严重回撤10%

    # 滑点配置
    max_slippage: float = 0.002             # 最大滑点0.2%
    slippage_warning: float = 0.001         # 滑点警告0.1%
    reject_high_slippage: bool = False      # 是否拒绝高滑点订单

    # 仓位限制
    max_position_pct: float = 0.20          # 单个标的最大仓位20%
    max_leverage: float = 1.0               # 最大杠杆

    # 订单限制
    max_order_value: float = 50000          # 单笔最大金额
    min_order_interval: float = 0.5         # 最小下单间隔(秒)
    max_orders_per_minute: int = 60         # 每分钟最大订单数

    # 交易时段限制
    allow_premarket: bool = True            # 允许盘前交易
    allow_afterhours: bool = True           # 允许盘后交易


@dataclass
class RiskCheckResult:
    """风控检查结果"""
    allowed: bool
    risk_level: RiskLevel
    reasons: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "allowed": self.allowed,
            "risk_level": self.risk_level.value,
            "reasons": self.reasons,
            "warnings": self.warnings,
            "timestamp": self.timestamp.isoformat()
        }


class RiskManager:
    """
    综合风险管理器
    整合所有风控模块，提供统一的风控接口
    """

    def __init__(self, config: Optional[RiskConfig] = None):
        self.config = config or RiskConfig()

        # 初始化各风控模块
        self._circuit_breaker = CircuitBreaker(CircuitBreakerConfig(
            daily_loss_threshold=self.config.daily_loss_threshold,
            single_loss_threshold=self.config.single_loss_threshold,
            consecutive_loss_count=self.config.consecutive_loss_count,
            recovery_time=self.config.recovery_time
        ))

        self._drawdown_monitor = DrawdownMonitor(DrawdownConfig(
            max_drawdown=self.config.max_drawdown,
            warning_threshold=self.config.warning_drawdown,
            critical_threshold=self.config.critical_drawdown
        ))

        self._slippage_checker = SlippageChecker(SlippageConfig(
            max_slippage=self.config.max_slippage,
            warning_threshold=self.config.slippage_warning,
            reject_high_slippage=self.config.reject_high_slippage
        ))

        # 订单频率限制
        self._order_timestamps: List[float] = []
        self._last_order_time = 0.0
        self._lock = threading.Lock()

        # 回调
        self._callbacks: Dict[str, List[Callable]] = {}

        # 注册子模块回调
        self._setup_callbacks()

    def _setup_callbacks(self):
        """设置子模块回调"""
        self._circuit_breaker.register_callback("on_trip", self._on_circuit_break)
        self._drawdown_monitor.register_callback("on_exceeded", self._on_drawdown_exceeded)
        self._slippage_checker.register_callback("on_violation", self._on_slippage_violation)

    def _on_circuit_break(self, reason: str, stats):
        """熔断触发回调"""
        logger.error(f"🚨 Circuit breaker triggered: {reason}")
        self._notify("on_halt", "circuit_breaker", reason)

    def _on_drawdown_exceeded(self, alert: DrawdownAlert):
        """回撤超限回调"""
        logger.error(f"🚨 Drawdown exceeded: {alert.message}")
        self._notify("on_halt", "drawdown", alert.message)

    def _on_slippage_violation(self, violation: SlippageViolation):
        """滑点违规回调"""
        logger.warning(f"⚠️ Slippage violation: {violation.symbol} {violation.slippage:.4%}")
        self._notify("on_slippage_violation", violation)

    def initialize(self, initial_equity: float):
        """初始化风控"""
        self._circuit_breaker.initialize(initial_equity)
        self._drawdown_monitor.initialize(initial_equity)
        logger.info(f"Risk manager initialized with equity: ${initial_equity:,.2f}")

    def update_equity(self, current_equity: float, trade_pnl: Optional[float] = None):
        """更新权益"""
        self._circuit_breaker.update_equity(current_equity, trade_pnl)
        self._drawdown_monitor.update(current_equity)

    def pre_trade_check(
        self,
        symbol: str,
        side: str,  # "long", "short", "flat"
        quantity: int,
        price: float,
        current_position_value: float = 0.0,
        total_equity: float = 0.0
    ) -> RiskCheckResult:
        """
        交易前风控检查

        Args:
            symbol: 股票代码
            side: 交易方向
            quantity: 数量
            price: 价格
            current_position_value: 当前该标的持仓市值
            total_equity: 总权益

        Returns:
            RiskCheckResult: 检查结果
        """
        result = RiskCheckResult(allowed=True, risk_level=RiskLevel.LOW)

        # 1. 检查熔断器状态
        if not self._circuit_breaker.can_trade():
            result.allowed = False
            result.risk_level = RiskLevel.HALTED
            result.reasons.append(f"Circuit breaker is {self._circuit_breaker.state.value}")
            return result

        # 2. 检查回撤
        if not self._drawdown_monitor.can_trade():
            result.allowed = False
            result.risk_level = RiskLevel.HALTED
            result.reasons.append(f"Drawdown exceeded: {self._drawdown_monitor.current_drawdown:.2%}")
            return result

        # 3. 检查订单频率
        with self._lock:
            now = time.time()

            # 最小间隔检查
            if now - self._last_order_time < self.config.min_order_interval:
                result.allowed = False
                result.risk_level = RiskLevel.HIGH
                result.reasons.append("Order interval too short")
                return result

            # 每分钟订单数检查
            self._order_timestamps = [t for t in self._order_timestamps if now - t < 60]
            if len(self._order_timestamps) >= self.config.max_orders_per_minute:
                result.allowed = False
                result.risk_level = RiskLevel.HIGH
                result.reasons.append("Max orders per minute exceeded")
                return result

        # 4. 检查订单金额
        order_value = quantity * price
        if order_value > self.config.max_order_value:
            result.allowed = False
            result.risk_level = RiskLevel.HIGH
            result.reasons.append(f"Order value ${order_value:,.2f} exceeds max ${self.config.max_order_value:,.2f}")
            return result

        # 5. 检查仓位限制
        if total_equity > 0:
            new_position_value = current_position_value + order_value if side == "long" else current_position_value
            position_pct = new_position_value / total_equity

            if position_pct > self.config.max_position_pct:
                result.allowed = False
                result.risk_level = RiskLevel.HIGH
                result.reasons.append(
                    f"Position {position_pct:.1%} would exceed max {self.config.max_position_pct:.1%}"
                )
                return result

        # 6. 设置风险级别和警告
        dd = self._drawdown_monitor.current_drawdown
        if dd >= self.config.critical_drawdown:
            result.risk_level = RiskLevel.HIGH
            result.warnings.append(f"High drawdown: {dd:.2%}")
        elif dd >= self.config.warning_drawdown:
            result.risk_level = RiskLevel.MEDIUM
            result.warnings.append(f"Elevated drawdown: {dd:.2%}")

        return result

    def post_trade_check(
        self,
        symbol: str,
        expected_price: float,
        executed_price: float,
        order_id: Optional[str] = None
    ) -> SlippageViolation:
        """
        交易后检查（滑点）

        Args:
            symbol: 股票代码
            expected_price: 预期价格
            executed_price: 成交价格
            order_id: 订单ID

        Returns:
            SlippageViolation: 滑点记录
        """
        # 记录订单时间
        with self._lock:
            self._last_order_time = time.time()
            self._order_timestamps.append(self._last_order_time)

        return self._slippage_checker.check_slippage(
            symbol, expected_price, executed_price, order_id
        )

    def force_halt(self, reason: str = "Manual halt"):
        """强制停止交易"""
        self._circuit_breaker.force_trip(reason)
        logger.warning(f"Trading halted: {reason}")

    def resume_trading(self):
        """恢复交易"""
        self._circuit_breaker.force_recover()
        self._drawdown_monitor.reset_exceeded()
        logger.info("Trading resumed")

    def register_callback(self, event: str, callback: Callable):
        """注册回调 (on_halt, on_slippage_violation)"""
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

    def get_risk_level(self) -> RiskLevel:
        """获取当前风险级别"""
        if not self._circuit_breaker.can_trade():
            return RiskLevel.HALTED
        if not self._drawdown_monitor.can_trade():
            return RiskLevel.HALTED

        dd = self._drawdown_monitor.current_drawdown
        daily_return = self._circuit_breaker.stats.daily_return

        if dd >= self.config.critical_drawdown or daily_return <= -0.02:
            return RiskLevel.CRITICAL
        if dd >= self.config.warning_drawdown or daily_return <= -0.01:
            return RiskLevel.HIGH
        if dd >= self.config.warning_drawdown / 2:
            return RiskLevel.MEDIUM

        return RiskLevel.LOW

    @property
    def circuit_breaker(self) -> CircuitBreaker:
        return self._circuit_breaker

    @property
    def drawdown_monitor(self) -> DrawdownMonitor:
        return self._drawdown_monitor

    @property
    def slippage_checker(self) -> SlippageChecker:
        return self._slippage_checker

    def get_status(self) -> Dict[str, Any]:
        """获取综合状态"""
        return {
            "risk_level": self.get_risk_level().value,
            "can_trade": self._circuit_breaker.can_trade() and self._drawdown_monitor.can_trade(),
            "circuit_breaker": self._circuit_breaker.get_status(),
            "drawdown": self._drawdown_monitor.get_status(),
            "slippage": self._slippage_checker.get_status(),
            "order_rate": {
                "orders_last_minute": len(self._order_timestamps),
                "max_per_minute": self.config.max_orders_per_minute,
                "min_interval": self.config.min_order_interval
            },
            "config": {
                "daily_loss_threshold": self.config.daily_loss_threshold,
                "max_drawdown": self.config.max_drawdown,
                "max_slippage": self.config.max_slippage,
                "max_position_pct": self.config.max_position_pct,
                "max_order_value": self.config.max_order_value
            }
        }


# 全局单例
_risk_manager: Optional[RiskManager] = None


def get_risk_manager(config: Optional[RiskConfig] = None) -> RiskManager:
    """获取风险管理器单例"""
    global _risk_manager
    if _risk_manager is None:
        _risk_manager = RiskManager(config)
    return _risk_manager
