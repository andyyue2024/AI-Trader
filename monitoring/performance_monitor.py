# -*- coding: utf-8 -*-
"""
性能监控器
监控系统性能指标：CPU、内存、延迟、吞吐量等
"""

import asyncio
import logging
import os
import platform
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class PerformanceSnapshot:
    """性能快照"""
    timestamp: datetime
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    memory_used_mb: float = 0.0
    disk_percent: float = 0.0
    network_sent_mb: float = 0.0
    network_recv_mb: float = 0.0
    active_threads: int = 0
    open_files: int = 0

    # 应用指标
    request_count: int = 0
    error_count: int = 0
    avg_latency_ms: float = 0.0
    max_latency_ms: float = 0.0
    throughput_per_sec: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "system": {
                "cpu_percent": round(self.cpu_percent, 2),
                "memory_percent": round(self.memory_percent, 2),
                "memory_used_mb": round(self.memory_used_mb, 2),
                "disk_percent": round(self.disk_percent, 2),
                "network_sent_mb": round(self.network_sent_mb, 2),
                "network_recv_mb": round(self.network_recv_mb, 2),
                "active_threads": self.active_threads,
                "open_files": self.open_files
            },
            "application": {
                "request_count": self.request_count,
                "error_count": self.error_count,
                "avg_latency_ms": round(self.avg_latency_ms, 3),
                "max_latency_ms": round(self.max_latency_ms, 3),
                "throughput_per_sec": round(self.throughput_per_sec, 2)
            }
        }


@dataclass
class LatencyRecord:
    """延迟记录"""
    operation: str
    start_time: float
    end_time: float = 0.0
    success: bool = True

    @property
    def duration_ms(self) -> float:
        if self.end_time == 0:
            return (time.perf_counter() - self.start_time) * 1000
        return (self.end_time - self.start_time) * 1000


class PerformanceMonitor:
    """
    性能监控器
    收集和分析系统性能指标
    """

    def __init__(
        self,
        collection_interval: float = 5.0,
        history_size: int = 1000,
        alert_thresholds: Dict[str, float] = None
    ):
        self.collection_interval = collection_interval
        self.history_size = history_size
        self.alert_thresholds = alert_thresholds or {
            "cpu_percent": 90.0,
            "memory_percent": 85.0,
            "disk_percent": 90.0,
            "avg_latency_ms": 100.0,
            "error_rate": 0.05
        }

        self._snapshots: deque = deque(maxlen=history_size)
        self._latencies: deque = deque(maxlen=10000)
        self._request_count = 0
        self._error_count = 0
        self._lock = threading.Lock()

        self._running = False
        self._collector_thread: Optional[threading.Thread] = None
        self._alert_callbacks: List[Callable] = []

        # 网络基线
        self._network_baseline = None

    def start(self):
        """启动监控"""
        if self._running:
            return

        self._running = True
        self._collector_thread = threading.Thread(target=self._collection_loop, daemon=True)
        self._collector_thread.start()
        logger.info("Performance monitor started")

    def stop(self):
        """停止监控"""
        self._running = False
        if self._collector_thread:
            self._collector_thread.join(timeout=5)
        logger.info("Performance monitor stopped")

    def _collection_loop(self):
        """收集循环"""
        while self._running:
            try:
                snapshot = self._collect_snapshot()

                with self._lock:
                    self._snapshots.append(snapshot)

                # 检查告警
                self._check_alerts(snapshot)

            except Exception as e:
                logger.error(f"Failed to collect performance data: {e}")

            time.sleep(self.collection_interval)

    def _collect_snapshot(self) -> PerformanceSnapshot:
        """收集性能快照"""
        snapshot = PerformanceSnapshot(timestamp=datetime.now())

        try:
            import psutil

            # CPU
            snapshot.cpu_percent = psutil.cpu_percent(interval=0.1)

            # 内存
            memory = psutil.virtual_memory()
            snapshot.memory_percent = memory.percent
            snapshot.memory_used_mb = memory.used / (1024 * 1024)

            # 磁盘
            disk = psutil.disk_usage('/')
            snapshot.disk_percent = disk.percent

            # 网络
            network = psutil.net_io_counters()
            if self._network_baseline is None:
                self._network_baseline = (network.bytes_sent, network.bytes_recv)
            snapshot.network_sent_mb = (network.bytes_sent - self._network_baseline[0]) / (1024 * 1024)
            snapshot.network_recv_mb = (network.bytes_recv - self._network_baseline[1]) / (1024 * 1024)

            # 线程
            snapshot.active_threads = threading.active_count()

            # 打开文件
            try:
                process = psutil.Process()
                snapshot.open_files = len(process.open_files())
            except:
                snapshot.open_files = 0

        except ImportError:
            # psutil 不可用，使用基本信息
            snapshot.active_threads = threading.active_count()
        except Exception as e:
            logger.debug(f"Failed to collect system metrics: {e}")

        # 应用指标
        with self._lock:
            snapshot.request_count = self._request_count
            snapshot.error_count = self._error_count

            if self._latencies:
                latencies = [l.duration_ms for l in self._latencies]
                snapshot.avg_latency_ms = sum(latencies) / len(latencies)
                snapshot.max_latency_ms = max(latencies)

                # 吞吐量
                recent_latencies = [l for l in self._latencies
                                  if time.perf_counter() - l.start_time < 60]
                snapshot.throughput_per_sec = len(recent_latencies) / 60.0

        return snapshot

    def _check_alerts(self, snapshot: PerformanceSnapshot):
        """检查告警条件"""
        alerts = []

        if snapshot.cpu_percent > self.alert_thresholds.get("cpu_percent", 90):
            alerts.append(("cpu", f"CPU usage high: {snapshot.cpu_percent}%"))

        if snapshot.memory_percent > self.alert_thresholds.get("memory_percent", 85):
            alerts.append(("memory", f"Memory usage high: {snapshot.memory_percent}%"))

        if snapshot.disk_percent > self.alert_thresholds.get("disk_percent", 90):
            alerts.append(("disk", f"Disk usage high: {snapshot.disk_percent}%"))

        if snapshot.avg_latency_ms > self.alert_thresholds.get("avg_latency_ms", 100):
            alerts.append(("latency", f"High latency: {snapshot.avg_latency_ms:.2f}ms"))

        # 错误率
        if snapshot.request_count > 0:
            error_rate = snapshot.error_count / snapshot.request_count
            if error_rate > self.alert_thresholds.get("error_rate", 0.05):
                alerts.append(("error_rate", f"High error rate: {error_rate:.2%}"))

        # 触发回调
        for alert_type, message in alerts:
            for callback in self._alert_callbacks:
                try:
                    callback(alert_type, message, snapshot)
                except Exception as e:
                    logger.error(f"Alert callback failed: {e}")

    def record_latency(self, operation: str) -> LatencyRecord:
        """开始记录延迟"""
        record = LatencyRecord(operation=operation, start_time=time.perf_counter())
        return record

    def end_latency(self, record: LatencyRecord, success: bool = True):
        """结束延迟记录"""
        record.end_time = time.perf_counter()
        record.success = success

        with self._lock:
            self._latencies.append(record)
            self._request_count += 1
            if not success:
                self._error_count += 1

    def record_request(self, success: bool = True, latency_ms: float = 0):
        """记录请求"""
        with self._lock:
            self._request_count += 1
            if not success:
                self._error_count += 1

            if latency_ms > 0:
                record = LatencyRecord(
                    operation="request",
                    start_time=time.perf_counter() - latency_ms/1000,
                    end_time=time.perf_counter(),
                    success=success
                )
                self._latencies.append(record)

    def add_alert_callback(self, callback: Callable):
        """添加告警回调"""
        self._alert_callbacks.append(callback)

    def get_current_stats(self) -> Dict[str, Any]:
        """获取当前统计"""
        with self._lock:
            if not self._snapshots:
                return {}
            return self._snapshots[-1].to_dict()

    def get_history(self, minutes: int = 60) -> List[Dict[str, Any]]:
        """获取历史数据"""
        cutoff = datetime.now() - timedelta(minutes=minutes)

        with self._lock:
            return [
                s.to_dict() for s in self._snapshots
                if s.timestamp >= cutoff
            ]

    def get_summary(self) -> Dict[str, Any]:
        """获取摘要统计"""
        with self._lock:
            snapshots = list(self._snapshots)

        if not snapshots:
            return {}

        return {
            "collection_period": {
                "start": snapshots[0].timestamp.isoformat(),
                "end": snapshots[-1].timestamp.isoformat(),
                "samples": len(snapshots)
            },
            "cpu": {
                "avg": sum(s.cpu_percent for s in snapshots) / len(snapshots),
                "max": max(s.cpu_percent for s in snapshots),
                "min": min(s.cpu_percent for s in snapshots)
            },
            "memory": {
                "avg": sum(s.memory_percent for s in snapshots) / len(snapshots),
                "max": max(s.memory_percent for s in snapshots)
            },
            "latency": {
                "avg_ms": sum(s.avg_latency_ms for s in snapshots) / len(snapshots),
                "max_ms": max(s.max_latency_ms for s in snapshots)
            },
            "requests": {
                "total": self._request_count,
                "errors": self._error_count,
                "error_rate": self._error_count / max(1, self._request_count)
            }
        }

    def reset_counters(self):
        """重置计数器"""
        with self._lock:
            self._request_count = 0
            self._error_count = 0
            self._latencies.clear()


class LatencyTimer:
    """延迟计时器上下文管理器"""

    def __init__(self, monitor: PerformanceMonitor, operation: str):
        self.monitor = monitor
        self.operation = operation
        self.record: Optional[LatencyRecord] = None
        self.success = True

    def __enter__(self):
        self.record = self.monitor.record_latency(self.operation)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.success = exc_type is None
        self.monitor.end_latency(self.record, self.success)
        return False


# 全局性能监控器
_performance_monitor: Optional[PerformanceMonitor] = None


def get_performance_monitor() -> PerformanceMonitor:
    """获取全局性能监控器"""
    global _performance_monitor
    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor()
    return _performance_monitor


def start_monitoring():
    """启动监控"""
    get_performance_monitor().start()


def stop_monitoring():
    """停止监控"""
    get_performance_monitor().stop()


def timer(operation: str) -> LatencyTimer:
    """创建计时器"""
    return LatencyTimer(get_performance_monitor(), operation)
