# -*- coding: utf-8 -*-
"""
监控模块
提供 Prometheus 指标导出、Grafana 仪表盘、飞书告警、错误跟踪、性能监控
"""

from .metrics_exporter import MetricsExporter, start_metrics_server
from .feishu_alert import FeishuAlert, send_feishu_alert
from .grafana_dashboard import generate_dashboard_json
from .error_tracker import (
    ErrorTracker, ErrorRecord, ErrorSeverity,
    get_error_tracker, track_error, track_exception
)
from .performance_monitor import (
    PerformanceMonitor, PerformanceSnapshot, LatencyTimer,
    get_performance_monitor, start_monitoring, stop_monitoring, timer
)
from .system_dashboard import (
    SystemDashboard, ComponentStatus, SystemAlert,
    get_dashboard, update_component, add_alert, get_health
)

__all__ = [
    # 指标导出
    'MetricsExporter',
    'start_metrics_server',
    # 飞书告警
    'FeishuAlert',
    'send_feishu_alert',
    # Grafana
    'generate_dashboard_json',
    # 错误跟踪
    'ErrorTracker',
    'ErrorRecord',
    'ErrorSeverity',
    'get_error_tracker',
    'track_error',
    'track_exception',
    # 性能监控
    'PerformanceMonitor',
    'PerformanceSnapshot',
    'LatencyTimer',
    'get_performance_monitor',
    'start_monitoring',
    'stop_monitoring',
    'timer',
    # 系统仪表盘
    'SystemDashboard',
    'ComponentStatus',
    'SystemAlert',
    'get_dashboard',
    'update_component',
    'add_alert',
    'get_health'
]
