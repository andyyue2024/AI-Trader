# -*- coding: utf-8 -*-
"""
系统仪表盘
提供系统状态的统一视图
"""

import json
import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ComponentStatus:
    """组件状态"""
    name: str
    status: str  # running, stopped, error, degraded
    last_update: datetime = field(default_factory=datetime.now)
    message: str = ""
    metrics: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_healthy(self) -> bool:
        return self.status in ["running", "degraded"]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "is_healthy": self.is_healthy,
            "last_update": self.last_update.isoformat(),
            "message": self.message,
            "metrics": self.metrics
        }


@dataclass
class SystemAlert:
    """系统告警"""
    alert_id: str
    timestamp: datetime
    level: str  # info, warning, error, critical
    source: str
    title: str
    message: str
    acknowledged: bool = False
    resolved: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "alert_id": self.alert_id,
            "timestamp": self.timestamp.isoformat(),
            "level": self.level,
            "source": self.source,
            "title": self.title,
            "message": self.message,
            "acknowledged": self.acknowledged,
            "resolved": self.resolved
        }


class SystemDashboard:
    """
    系统仪表盘
    统一展示系统各组件状态
    """

    def __init__(self):
        self._components: Dict[str, ComponentStatus] = {}
        self._alerts: List[SystemAlert] = []
        self._metrics: Dict[str, Any] = {}
        self._lock = threading.Lock()
        self._alert_counter = 0
        self._listeners: List[Callable] = []

        # 初始化核心组件
        self._init_core_components()

    def _init_core_components(self):
        """初始化核心组件"""
        core_components = [
            "OpenD Connection",
            "Trade Executor",
            "Quote Subscriber",
            "Risk Manager",
            "Performance Analyzer",
            "Session Manager",
            "Metrics Exporter",
            "Alert Service"
        ]

        for name in core_components:
            self._components[name] = ComponentStatus(
                name=name,
                status="stopped",
                message="Not initialized"
            )

    def register_component(self, name: str, status: str = "stopped", message: str = ""):
        """注册组件"""
        with self._lock:
            self._components[name] = ComponentStatus(
                name=name,
                status=status,
                message=message
            )
        self._notify_listeners()

    def update_component(
        self,
        name: str,
        status: str = None,
        message: str = None,
        metrics: Dict[str, Any] = None
    ):
        """更新组件状态"""
        with self._lock:
            if name not in self._components:
                self._components[name] = ComponentStatus(name=name, status="unknown")

            component = self._components[name]
            component.last_update = datetime.now()

            if status:
                component.status = status
            if message is not None:
                component.message = message
            if metrics:
                component.metrics.update(metrics)

        self._notify_listeners()

    def get_component(self, name: str) -> Optional[ComponentStatus]:
        """获取组件状态"""
        with self._lock:
            return self._components.get(name)

    def get_all_components(self) -> Dict[str, Dict[str, Any]]:
        """获取所有组件状态"""
        with self._lock:
            return {name: c.to_dict() for name, c in self._components.items()}

    def add_alert(
        self,
        level: str,
        source: str,
        title: str,
        message: str
    ) -> SystemAlert:
        """添加告警"""
        with self._lock:
            self._alert_counter += 1
            alert = SystemAlert(
                alert_id=f"ALERT-{datetime.now().strftime('%Y%m%d')}-{self._alert_counter:06d}",
                timestamp=datetime.now(),
                level=level,
                source=source,
                title=title,
                message=message
            )
            self._alerts.append(alert)

            # 限制告警数量
            if len(self._alerts) > 1000:
                self._alerts = self._alerts[-500:]

        self._notify_listeners()
        return alert

    def acknowledge_alert(self, alert_id: str) -> bool:
        """确认告警"""
        with self._lock:
            for alert in self._alerts:
                if alert.alert_id == alert_id:
                    alert.acknowledged = True
                    return True
        return False

    def resolve_alert(self, alert_id: str) -> bool:
        """解决告警"""
        with self._lock:
            for alert in self._alerts:
                if alert.alert_id == alert_id:
                    alert.resolved = True
                    return True
        return False

    def get_alerts(
        self,
        level: str = None,
        unresolved_only: bool = False,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """获取告警列表"""
        with self._lock:
            alerts = self._alerts.copy()

        if level:
            alerts = [a for a in alerts if a.level == level]
        if unresolved_only:
            alerts = [a for a in alerts if not a.resolved]

        return [a.to_dict() for a in alerts[-limit:]]

    def set_metric(self, key: str, value: Any):
        """设置指标"""
        with self._lock:
            self._metrics[key] = {
                "value": value,
                "updated_at": datetime.now().isoformat()
            }

    def get_metrics(self) -> Dict[str, Any]:
        """获取所有指标"""
        with self._lock:
            return self._metrics.copy()

    def get_system_health(self) -> Dict[str, Any]:
        """获取系统健康状态"""
        with self._lock:
            components = list(self._components.values())
            alerts = [a for a in self._alerts if not a.resolved]

        total = len(components)
        healthy = sum(1 for c in components if c.is_healthy)

        # 计算健康分数
        health_score = (healthy / total * 100) if total > 0 else 0

        # 告警影响
        critical_alerts = sum(1 for a in alerts if a.level == "critical")
        error_alerts = sum(1 for a in alerts if a.level == "error")

        if critical_alerts > 0:
            health_score = min(health_score, 50)
        elif error_alerts > 0:
            health_score = min(health_score, 75)

        # 确定总体状态
        if health_score >= 90:
            overall_status = "healthy"
        elif health_score >= 70:
            overall_status = "degraded"
        elif health_score >= 50:
            overall_status = "warning"
        else:
            overall_status = "critical"

        return {
            "overall_status": overall_status,
            "health_score": round(health_score, 1),
            "components": {
                "total": total,
                "healthy": healthy,
                "unhealthy": total - healthy
            },
            "alerts": {
                "total": len(alerts),
                "critical": critical_alerts,
                "error": error_alerts,
                "warning": sum(1 for a in alerts if a.level == "warning")
            },
            "timestamp": datetime.now().isoformat()
        }

    def get_dashboard_data(self) -> Dict[str, Any]:
        """获取完整仪表盘数据"""
        return {
            "health": self.get_system_health(),
            "components": self.get_all_components(),
            "alerts": self.get_alerts(unresolved_only=True, limit=10),
            "metrics": self.get_metrics()
        }

    def add_listener(self, callback: Callable):
        """添加监听器"""
        self._listeners.append(callback)

    def _notify_listeners(self):
        """通知监听器"""
        data = self.get_dashboard_data()
        for listener in self._listeners:
            try:
                listener(data)
            except Exception as e:
                logger.error(f"Listener callback failed: {e}")

    def export_status(self, filepath: str):
        """导出状态到文件"""
        data = self.get_dashboard_data()
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)


# 全局仪表盘实例
_dashboard: Optional[SystemDashboard] = None


def get_dashboard() -> SystemDashboard:
    """获取全局仪表盘"""
    global _dashboard
    if _dashboard is None:
        _dashboard = SystemDashboard()
    return _dashboard


def update_component(name: str, **kwargs):
    """快捷更新组件"""
    get_dashboard().update_component(name, **kwargs)


def add_alert(level: str, source: str, title: str, message: str):
    """快捷添加告警"""
    return get_dashboard().add_alert(level, source, title, message)


def get_health():
    """快捷获取健康状态"""
    return get_dashboard().get_system_health()
