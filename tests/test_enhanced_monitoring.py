# -*- coding: utf-8 -*-
"""
增强监控模块单元测试
"""

import os
import pytest
import threading
import time
from datetime import datetime, timedelta

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from monitoring.error_tracker import (
    ErrorTracker, ErrorRecord, ErrorSeverity,
    get_error_tracker, track_error, track_exception
)
from monitoring.performance_monitor import (
    PerformanceMonitor, PerformanceSnapshot, LatencyTimer,
    get_performance_monitor, timer
)
from monitoring.system_dashboard import (
    SystemDashboard, ComponentStatus, SystemAlert,
    get_dashboard, update_component, add_alert, get_health
)


class TestErrorRecord:
    """错误记录测试"""

    def test_basic_record(self):
        """测试基本记录"""
        record = ErrorRecord(
            error_id="ERR-001",
            timestamp=datetime.now(),
            severity=ErrorSeverity.ERROR,
            error_type="ValueError",
            message="Test error"
        )

        assert record.error_id == "ERR-001"
        assert record.severity == ErrorSeverity.ERROR
        assert record.resolved == False

    def test_to_dict(self):
        """测试转换为字典"""
        record = ErrorRecord(
            error_id="ERR-002",
            timestamp=datetime.now(),
            severity=ErrorSeverity.WARNING,
            error_type="RuntimeWarning",
            message="Test warning"
        )

        d = record.to_dict()

        assert d["error_id"] == "ERR-002"
        assert d["severity"] == "warning"
        assert "timestamp" in d


class TestErrorTracker:
    """错误跟踪器测试"""

    @pytest.fixture
    def tracker(self, tmp_path):
        return ErrorTracker(log_dir=str(tmp_path / "errors"))

    def test_track_error(self, tracker):
        """测试跟踪错误"""
        record = tracker.track_error(
            "Test error message",
            error_type="TestError",
            severity=ErrorSeverity.ERROR
        )

        assert record.error_id is not None
        assert record.message == "Test error message"

    def test_track_exception(self, tracker):
        """测试跟踪异常"""
        try:
            raise ValueError("Test exception")
        except ValueError as e:
            record = tracker.track_exception(e)

        assert record.error_type == "ValueError"
        assert "Test exception" in record.message
        assert record.traceback != ""

    def test_get_errors(self, tracker):
        """测试获取错误列表"""
        tracker.track_error("Error 1")
        tracker.track_error("Error 2")
        tracker.track_error("Warning 1", severity=ErrorSeverity.WARNING)

        all_errors = tracker.get_errors()
        assert len(all_errors) == 3

        error_only = tracker.get_errors(severity=ErrorSeverity.ERROR)
        assert len(error_only) == 2

    def test_get_error_stats(self, tracker):
        """测试获取错误统计"""
        tracker.track_error("Error 1")
        tracker.track_error("Warning 1", severity=ErrorSeverity.WARNING)

        stats = tracker.get_error_stats()

        assert stats["total_errors"] == 2
        assert stats["by_severity"]["error"] == 1
        assert stats["by_severity"]["warning"] == 1

    def test_resolve_error(self, tracker):
        """测试解决错误"""
        record = tracker.track_error("To be resolved")

        assert record.resolved == False

        result = tracker.resolve_error(record.error_id)

        assert result == True
        assert record.resolved == True
        assert record.resolution_time is not None

    def test_alert_callback(self, tracker):
        """测试告警回调"""
        alerts = []

        tracker.alert_callback = lambda r: alerts.append(r)

        tracker.track_error("Critical error", severity=ErrorSeverity.CRITICAL)

        assert len(alerts) == 1
        assert alerts[0].severity == ErrorSeverity.CRITICAL


class TestPerformanceSnapshot:
    """性能快照测试"""

    def test_basic_snapshot(self):
        """测试基本快照"""
        snapshot = PerformanceSnapshot(
            timestamp=datetime.now(),
            cpu_percent=50.0,
            memory_percent=60.0,
            avg_latency_ms=5.0
        )

        assert snapshot.cpu_percent == 50.0
        assert snapshot.memory_percent == 60.0

    def test_to_dict(self):
        """测试转换为字典"""
        snapshot = PerformanceSnapshot(
            timestamp=datetime.now(),
            cpu_percent=45.5,
            memory_percent=55.5,
            request_count=100,
            error_count=5
        )

        d = snapshot.to_dict()

        assert "system" in d
        assert "application" in d
        assert d["system"]["cpu_percent"] == 45.5


class TestPerformanceMonitor:
    """性能监控器测试"""

    @pytest.fixture
    def monitor(self):
        m = PerformanceMonitor(collection_interval=0.1)
        yield m
        m.stop()

    def test_record_latency(self, monitor):
        """测试记录延迟"""
        record = monitor.record_latency("test_operation")

        time.sleep(0.01)

        monitor.end_latency(record)

        assert record.duration_ms >= 10

    def test_record_request(self, monitor):
        """测试记录请求"""
        monitor.record_request(success=True, latency_ms=5.0)
        monitor.record_request(success=False, latency_ms=10.0)

        assert monitor._request_count == 2
        assert monitor._error_count == 1

    def test_timer_context_manager(self, monitor):
        """测试计时器上下文管理器"""
        with LatencyTimer(monitor, "test_op") as t:
            time.sleep(0.01)

        assert t.success == True
        assert t.record.duration_ms >= 10

    def test_get_summary(self, monitor):
        """测试获取摘要"""
        monitor.record_request(success=True, latency_ms=5.0)
        monitor.record_request(success=True, latency_ms=10.0)

        # 手动添加快照
        from monitoring.performance_monitor import PerformanceSnapshot
        snapshot = PerformanceSnapshot(
            timestamp=datetime.now(),
            cpu_percent=50.0,
            memory_percent=60.0
        )
        monitor._snapshots.append(snapshot)

        summary = monitor.get_summary()

        assert "cpu" in summary
        assert "requests" in summary
        assert summary["requests"]["total"] == 2

    def test_alert_callback(self, monitor):
        """测试告警回调"""
        alerts = []

        monitor.add_alert_callback(
            lambda t, m, s: alerts.append((t, m))
        )

        monitor.alert_thresholds["cpu_percent"] = 0  # 设置低阈值

        # 添加高 CPU 快照
        from monitoring.performance_monitor import PerformanceSnapshot
        snapshot = PerformanceSnapshot(
            timestamp=datetime.now(),
            cpu_percent=95.0
        )
        monitor._check_alerts(snapshot)

        assert len(alerts) > 0
        assert alerts[0][0] == "cpu"


class TestComponentStatus:
    """组件状态测试"""

    def test_basic_status(self):
        """测试基本状态"""
        status = ComponentStatus(
            name="TestComponent",
            status="running"
        )

        assert status.name == "TestComponent"
        assert status.is_healthy == True

    def test_unhealthy_status(self):
        """测试不健康状态"""
        status = ComponentStatus(
            name="FailedComponent",
            status="error"
        )

        assert status.is_healthy == False


class TestSystemDashboard:
    """系统仪表盘测试"""

    @pytest.fixture
    def dashboard(self):
        return SystemDashboard()

    def test_register_component(self, dashboard):
        """测试注册组件"""
        dashboard.register_component("TestComponent", "running", "All good")

        component = dashboard.get_component("TestComponent")

        assert component is not None
        assert component.status == "running"

    def test_update_component(self, dashboard):
        """测试更新组件"""
        dashboard.register_component("TestComponent", "stopped")
        dashboard.update_component("TestComponent", status="running", message="Started")

        component = dashboard.get_component("TestComponent")

        assert component.status == "running"
        assert component.message == "Started"

    def test_add_alert(self, dashboard):
        """测试添加告警"""
        alert = dashboard.add_alert(
            level="warning",
            source="TestSource",
            title="Test Alert",
            message="This is a test"
        )

        assert alert.alert_id is not None
        assert alert.level == "warning"

    def test_acknowledge_alert(self, dashboard):
        """测试确认告警"""
        alert = dashboard.add_alert("info", "test", "Test", "Test message")

        assert alert.acknowledged == False

        result = dashboard.acknowledge_alert(alert.alert_id)

        assert result == True
        assert alert.acknowledged == True

    def test_get_system_health(self, dashboard):
        """测试获取系统健康状态"""
        dashboard.register_component("C1", "running")
        dashboard.register_component("C2", "running")
        dashboard.register_component("C3", "error")

        health = dashboard.get_system_health()

        assert "overall_status" in health
        assert "health_score" in health
        assert health["components"]["healthy"] == 2
        assert health["components"]["unhealthy"] == 1

    def test_critical_alert_affects_health(self, dashboard):
        """测试严重告警影响健康分数"""
        dashboard.register_component("C1", "running")
        dashboard.add_alert("critical", "test", "Critical", "Critical issue")

        health = dashboard.get_system_health()

        assert health["health_score"] <= 50

    def test_get_dashboard_data(self, dashboard):
        """测试获取仪表盘数据"""
        dashboard.register_component("TestComponent", "running")
        dashboard.add_alert("info", "test", "Test", "Test")
        dashboard.set_metric("test_metric", 123)

        data = dashboard.get_dashboard_data()

        assert "health" in data
        assert "components" in data
        assert "alerts" in data
        assert "metrics" in data


class TestGlobalFunctions:
    """全局函数测试"""

    def test_get_error_tracker(self):
        """测试获取错误跟踪器"""
        tracker = get_error_tracker()
        assert tracker is not None

    def test_get_performance_monitor(self):
        """测试获取性能监控器"""
        monitor = get_performance_monitor()
        assert monitor is not None

    def test_get_dashboard(self):
        """测试获取仪表盘"""
        dashboard = get_dashboard()
        assert dashboard is not None

    def test_timer_function(self):
        """测试计时器函数"""
        with timer("test_operation") as t:
            time.sleep(0.01)

        assert t.record.duration_ms >= 10


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
