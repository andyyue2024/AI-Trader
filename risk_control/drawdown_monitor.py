# -*- coding: utf-8 -*-
"""
回撤监控器
实现最大回撤15%限制
"""

import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime, date
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DrawdownAlertLevel(Enum):
    """回撤警报级别"""
    NORMAL = "normal"       # 正常 (<5%)
    WARNING = "warning"     # 警告 (5%-10%)
    CRITICAL = "critical"   # 严重 (10%-15%)
    EXCEEDED = "exceeded"   # 超限 (>15%)


@dataclass
class DrawdownAlert:
    """回撤警报"""
    level: DrawdownAlertLevel
    current_drawdown: float
    peak_equity: float
    current_equity: float
    threshold: float
    timestamp: datetime = field(default_factory=datetime.now)
    message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "level": self.level.value,
            "current_drawdown": round(self.current_drawdown, 4),
            "peak_equity": self.peak_equity,
            "current_equity": self.current_equity,
            "threshold": self.threshold,
            "timestamp": self.timestamp.isoformat(),
            "message": self.message
        }


@dataclass
class DrawdownConfig:
    """回撤监控配置"""
    # 最大允许回撤
    max_drawdown: float = 0.15              # 15%
    # 警告阈值
    warning_threshold: float = 0.05         # 5%
    critical_threshold: float = 0.10        # 10%
    # 是否在超限时自动停止交易
    auto_stop_on_exceed: bool = True
    # 回撤计算周期
    rolling_window_days: int = 0            # 0表示从初始开始计算


class DrawdownMonitor:
    """
    回撤监控器
    实时监控投资组合回撤，在超过阈值时发出警报
    """

    def __init__(self, config: Optional[DrawdownConfig] = None):
        self.config = config or DrawdownConfig()
        self._peak_equity = 0.0
        self._current_equity = 0.0
        self._initial_equity = 0.0
        self._current_drawdown = 0.0
        self._max_recorded_drawdown = 0.0
        self._exceeded = False
        self._lock = threading.Lock()
        self._callbacks: Dict[str, List[Callable]] = {}
        self._history: List[Tuple[datetime, float, float]] = []  # (time, equity, drawdown)

    def initialize(self, initial_equity: float):
        """初始化监控器"""
        with self._lock:
            self._initial_equity = initial_equity
            self._peak_equity = initial_equity
            self._current_equity = initial_equity
            self._current_drawdown = 0.0
            self._max_recorded_drawdown = 0.0
            self._exceeded = False
            self._history.clear()

        logger.info(f"Drawdown monitor initialized with equity: ${initial_equity:,.2f}")

    def update(self, current_equity: float) -> Optional[DrawdownAlert]:
        """更新权益并检查回撤"""
        with self._lock:
            self._current_equity = current_equity

            # 更新峰值
            if current_equity > self._peak_equity:
                self._peak_equity = current_equity

            # 计算回撤
            if self._peak_equity > 0:
                self._current_drawdown = (self._peak_equity - current_equity) / self._peak_equity
            else:
                self._current_drawdown = 0.0

            # 更新最大记录回撤
            if self._current_drawdown > self._max_recorded_drawdown:
                self._max_recorded_drawdown = self._current_drawdown

            # 记录历史
            self._history.append((datetime.now(), current_equity, self._current_drawdown))

            # 限制历史记录数量
            if len(self._history) > 10000:
                self._history = self._history[-5000:]

        # 检查并生成警报
        alert = self._check_thresholds()

        if alert:
            self._notify_alert(alert)

        return alert

    def _check_thresholds(self) -> Optional[DrawdownAlert]:
        """检查回撤阈值"""
        dd = self._current_drawdown

        if dd >= self.config.max_drawdown:
            self._exceeded = True
            return DrawdownAlert(
                level=DrawdownAlertLevel.EXCEEDED,
                current_drawdown=dd,
                peak_equity=self._peak_equity,
                current_equity=self._current_equity,
                threshold=self.config.max_drawdown,
                message=f"CRITICAL: Drawdown {dd:.2%} exceeded max threshold {self.config.max_drawdown:.2%}!"
            )

        if dd >= self.config.critical_threshold:
            return DrawdownAlert(
                level=DrawdownAlertLevel.CRITICAL,
                current_drawdown=dd,
                peak_equity=self._peak_equity,
                current_equity=self._current_equity,
                threshold=self.config.critical_threshold,
                message=f"Critical drawdown alert: {dd:.2%}"
            )

        if dd >= self.config.warning_threshold:
            return DrawdownAlert(
                level=DrawdownAlertLevel.WARNING,
                current_drawdown=dd,
                peak_equity=self._peak_equity,
                current_equity=self._current_equity,
                threshold=self.config.warning_threshold,
                message=f"Drawdown warning: {dd:.2%}"
            )

        return None

    def _notify_alert(self, alert: DrawdownAlert):
        """发送警报通知"""
        event = f"on_{alert.level.value}"
        for cb in self._callbacks.get(event, []) + self._callbacks.get("on_alert", []):
            try:
                cb(alert)
            except Exception as e:
                logger.error(f"Alert callback error: {e}")

        # 记录日志
        if alert.level == DrawdownAlertLevel.EXCEEDED:
            logger.error(f"🚨 {alert.message}")
        elif alert.level == DrawdownAlertLevel.CRITICAL:
            logger.warning(f"⚠️ {alert.message}")
        elif alert.level == DrawdownAlertLevel.WARNING:
            logger.warning(f"⚡ {alert.message}")

    def register_callback(self, event: str, callback: Callable):
        """注册回调 (on_warning, on_critical, on_exceeded, on_alert)"""
        if event not in self._callbacks:
            self._callbacks[event] = []
        self._callbacks[event].append(callback)

    def can_trade(self) -> bool:
        """检查是否允许交易"""
        if self.config.auto_stop_on_exceed and self._exceeded:
            return False
        return True

    def reset_exceeded(self):
        """重置超限标记"""
        with self._lock:
            self._exceeded = False
        logger.info("Drawdown exceeded flag reset")

    @property
    def current_drawdown(self) -> float:
        return self._current_drawdown

    @property
    def max_drawdown(self) -> float:
        return self._max_recorded_drawdown

    @property
    def peak_equity(self) -> float:
        return self._peak_equity

    @property
    def current_equity(self) -> float:
        return self._current_equity

    @property
    def is_exceeded(self) -> bool:
        return self._exceeded

    def get_status(self) -> Dict[str, Any]:
        """获取监控状态"""
        alert_level = DrawdownAlertLevel.NORMAL
        if self._current_drawdown >= self.config.max_drawdown:
            alert_level = DrawdownAlertLevel.EXCEEDED
        elif self._current_drawdown >= self.config.critical_threshold:
            alert_level = DrawdownAlertLevel.CRITICAL
        elif self._current_drawdown >= self.config.warning_threshold:
            alert_level = DrawdownAlertLevel.WARNING

        return {
            "current_drawdown": round(self._current_drawdown, 4),
            "max_recorded_drawdown": round(self._max_recorded_drawdown, 4),
            "peak_equity": self._peak_equity,
            "current_equity": self._current_equity,
            "initial_equity": self._initial_equity,
            "alert_level": alert_level.value,
            "is_exceeded": self._exceeded,
            "can_trade": self.can_trade(),
            "thresholds": {
                "warning": self.config.warning_threshold,
                "critical": self.config.critical_threshold,
                "max": self.config.max_drawdown
            }
        }

    def get_history(self, last_n: int = 100) -> List[Dict[str, Any]]:
        """获取历史记录"""
        with self._lock:
            history = self._history[-last_n:] if last_n else self._history
            return [
                {
                    "timestamp": h[0].isoformat(),
                    "equity": h[1],
                    "drawdown": round(h[2], 4)
                }
                for h in history
            ]
