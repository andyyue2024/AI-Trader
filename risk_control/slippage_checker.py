# -*- coding: utf-8 -*-
"""
滑点检查器
确保滑点 ≤ 0.2%
"""

import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class SlippageViolation:
    """滑点违规记录"""
    symbol: str
    expected_price: float
    executed_price: float
    slippage: float
    threshold: float
    order_id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def is_violation(self) -> bool:
        return abs(self.slippage) > self.threshold

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "expected_price": self.expected_price,
            "executed_price": self.executed_price,
            "slippage": round(self.slippage, 6),
            "slippage_pct": f"{self.slippage:.4%}",
            "threshold": self.threshold,
            "is_violation": self.is_violation,
            "order_id": self.order_id,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class SlippageConfig:
    """滑点配置"""
    # 最大允许滑点
    max_slippage: float = 0.002             # 0.2%
    # 警告阈值
    warning_threshold: float = 0.001        # 0.1%
    # 是否拒绝高滑点订单
    reject_high_slippage: bool = False
    # 统计窗口大小
    stats_window_size: int = 100


class SlippageChecker:
    """
    滑点检查器
    监控和验证交易滑点
    """

    def __init__(self, config: Optional[SlippageConfig] = None):
        self.config = config or SlippageConfig()
        self._violations: List[SlippageViolation] = []
        self._all_slippages: List[float] = []
        self._lock = threading.Lock()
        self._callbacks: Dict[str, List[Callable]] = {}

        # 统计
        self._total_orders = 0
        self._violation_count = 0
        self._total_slippage = 0.0

    def check_slippage(
        self,
        symbol: str,
        expected_price: float,
        executed_price: float,
        order_id: Optional[str] = None
    ) -> SlippageViolation:
        """
        检查滑点

        Args:
            symbol: 股票代码
            expected_price: 预期价格
            executed_price: 成交价格
            order_id: 订单ID

        Returns:
            SlippageViolation: 滑点记录
        """
        # 计算滑点
        if expected_price > 0:
            slippage = (executed_price - expected_price) / expected_price
        else:
            slippage = 0.0

        violation = SlippageViolation(
            symbol=symbol,
            expected_price=expected_price,
            executed_price=executed_price,
            slippage=slippage,
            threshold=self.config.max_slippage,
            order_id=order_id
        )

        with self._lock:
            self._total_orders += 1
            self._total_slippage += abs(slippage)
            self._all_slippages.append(abs(slippage))

            # 限制历史记录
            if len(self._all_slippages) > self.config.stats_window_size:
                self._all_slippages = self._all_slippages[-self.config.stats_window_size:]

            if violation.is_violation:
                self._violation_count += 1
                self._violations.append(violation)

                # 限制违规记录
                if len(self._violations) > 1000:
                    self._violations = self._violations[-500:]

        # 发送通知
        if violation.is_violation:
            logger.warning(f"⚠️ Slippage violation: {symbol} {slippage:.4%} > {self.config.max_slippage:.4%}")
            self._notify("on_violation", violation)
        elif abs(slippage) > self.config.warning_threshold:
            logger.info(f"⚡ Slippage warning: {symbol} {slippage:.4%}")
            self._notify("on_warning", violation)

        return violation

    def can_execute(
        self,
        symbol: str,
        expected_price: float,
        bid_price: float,
        ask_price: float
    ) -> bool:
        """
        预检查是否可以执行（基于当前买卖价差）

        Args:
            symbol: 股票代码
            expected_price: 预期价格
            bid_price: 买一价
            ask_price: 卖一价

        Returns:
            bool: 是否可以执行
        """
        if not self.config.reject_high_slippage:
            return True

        # 估算最大可能滑点
        if expected_price > 0:
            max_potential_slippage = max(
                abs(ask_price - expected_price) / expected_price,
                abs(bid_price - expected_price) / expected_price
            )
        else:
            return True

        if max_potential_slippage > self.config.max_slippage:
            logger.warning(
                f"Order rejected due to potential slippage: {symbol} "
                f"bid={bid_price}, ask={ask_price}, expected={expected_price}"
            )
            return False

        return True

    def register_callback(self, event: str, callback: Callable):
        """注册回调 (on_violation, on_warning)"""
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
    def average_slippage(self) -> float:
        """平均滑点"""
        with self._lock:
            if self._all_slippages:
                return sum(self._all_slippages) / len(self._all_slippages)
            return 0.0

    @property
    def violation_rate(self) -> float:
        """违规率"""
        if self._total_orders > 0:
            return self._violation_count / self._total_orders
        return 0.0

    def get_status(self) -> Dict[str, Any]:
        """获取状态"""
        with self._lock:
            recent_slippages = self._all_slippages[-20:] if self._all_slippages else []

        return {
            "total_orders": self._total_orders,
            "violation_count": self._violation_count,
            "violation_rate": round(self.violation_rate, 4),
            "average_slippage": round(self.average_slippage, 6),
            "average_slippage_pct": f"{self.average_slippage:.4%}",
            "max_allowed_slippage": self.config.max_slippage,
            "recent_slippages": [round(s, 6) for s in recent_slippages],
            "config": {
                "max_slippage": self.config.max_slippage,
                "warning_threshold": self.config.warning_threshold,
                "reject_high_slippage": self.config.reject_high_slippage
            }
        }

    def get_violations(self, last_n: int = 50) -> List[Dict[str, Any]]:
        """获取违规记录"""
        with self._lock:
            violations = self._violations[-last_n:] if last_n else self._violations
            return [v.to_dict() for v in violations]

    def reset_stats(self):
        """重置统计"""
        with self._lock:
            self._total_orders = 0
            self._violation_count = 0
            self._total_slippage = 0.0
            self._all_slippages.clear()
            self._violations.clear()
        logger.info("Slippage stats reset")
