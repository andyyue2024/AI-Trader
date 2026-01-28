# -*- coding: utf-8 -*-
"""
增强错误跟踪器
记录、分析和报告系统错误
"""

import json
import logging
import os
import sys
import threading
import traceback
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """错误严重程度"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class ErrorRecord:
    """错误记录"""
    error_id: str
    timestamp: datetime
    severity: ErrorSeverity
    error_type: str
    message: str
    module: str = ""
    function: str = ""
    line_number: int = 0
    traceback: str = ""
    context: Dict[str, Any] = field(default_factory=dict)
    resolved: bool = False
    resolution_time: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "error_id": self.error_id,
            "timestamp": self.timestamp.isoformat(),
            "severity": self.severity.value,
            "error_type": self.error_type,
            "message": self.message,
            "module": self.module,
            "function": self.function,
            "line_number": self.line_number,
            "traceback": self.traceback,
            "context": self.context,
            "resolved": self.resolved,
            "resolution_time": self.resolution_time.isoformat() if self.resolution_time else None
        }


class ErrorTracker:
    """
    错误跟踪器
    记录和分析系统中的错误
    """

    def __init__(
        self,
        max_errors: int = 1000,
        log_dir: str = "./logs/errors",
        alert_callback: Optional[Callable[[ErrorRecord], None]] = None
    ):
        self.max_errors = max_errors
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.alert_callback = alert_callback

        self._errors: deque = deque(maxlen=max_errors)
        self._error_counts: Dict[str, int] = {}
        self._lock = threading.Lock()
        self._error_id_counter = 0

        # 设置全局异常处理
        self._original_excepthook = sys.excepthook
        sys.excepthook = self._exception_handler

    def _generate_error_id(self) -> str:
        """生成错误 ID"""
        self._error_id_counter += 1
        return f"ERR-{datetime.now().strftime('%Y%m%d')}-{self._error_id_counter:06d}"

    def _exception_handler(self, exc_type, exc_value, exc_tb):
        """全局异常处理器"""
        # 记录异常
        self.track_exception(exc_value, exc_tb)
        # 调用原始处理器
        self._original_excepthook(exc_type, exc_value, exc_tb)

    def track_exception(
        self,
        exception: Exception,
        tb=None,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        context: Dict[str, Any] = None
    ) -> ErrorRecord:
        """跟踪异常"""
        if tb is None:
            tb = exception.__traceback__

        # 提取堆栈信息
        tb_lines = traceback.format_exception(type(exception), exception, tb)
        tb_str = "".join(tb_lines)

        # 获取发生位置
        if tb:
            frame = traceback.extract_tb(tb)[-1] if traceback.extract_tb(tb) else None
            module = frame.filename if frame else ""
            function = frame.name if frame else ""
            line_number = frame.lineno if frame else 0
        else:
            module = function = ""
            line_number = 0

        record = ErrorRecord(
            error_id=self._generate_error_id(),
            timestamp=datetime.now(),
            severity=severity,
            error_type=type(exception).__name__,
            message=str(exception),
            module=module,
            function=function,
            line_number=line_number,
            traceback=tb_str,
            context=context or {}
        )

        self._add_record(record)
        return record

    def track_error(
        self,
        message: str,
        error_type: str = "Error",
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        context: Dict[str, Any] = None
    ) -> ErrorRecord:
        """跟踪错误消息"""
        # 获取调用位置
        frame = sys._getframe(1)

        record = ErrorRecord(
            error_id=self._generate_error_id(),
            timestamp=datetime.now(),
            severity=severity,
            error_type=error_type,
            message=message,
            module=frame.f_code.co_filename,
            function=frame.f_code.co_name,
            line_number=frame.f_lineno,
            context=context or {}
        )

        self._add_record(record)
        return record

    def _add_record(self, record: ErrorRecord):
        """添加错误记录"""
        with self._lock:
            self._errors.append(record)

            # 更新计数
            key = f"{record.error_type}:{record.module}"
            self._error_counts[key] = self._error_counts.get(key, 0) + 1

        # 记录到日志
        log_level = getattr(logging, record.severity.value.upper(), logging.ERROR)
        logger.log(log_level, f"[{record.error_id}] {record.error_type}: {record.message}")

        # 持久化到文件
        self._persist_error(record)

        # 触发告警
        if record.severity in [ErrorSeverity.ERROR, ErrorSeverity.CRITICAL]:
            if self.alert_callback:
                try:
                    self.alert_callback(record)
                except Exception as e:
                    logger.error(f"Alert callback failed: {e}")

    def _persist_error(self, record: ErrorRecord):
        """持久化错误到文件"""
        try:
            date_str = record.timestamp.strftime("%Y-%m-%d")
            log_file = self.log_dir / f"errors_{date_str}.jsonl"

            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(record.to_dict(), ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error(f"Failed to persist error: {e}")

    def get_errors(
        self,
        severity: ErrorSeverity = None,
        error_type: str = None,
        since: datetime = None,
        limit: int = 100
    ) -> List[ErrorRecord]:
        """获取错误列表"""
        with self._lock:
            errors = list(self._errors)

        # 过滤
        if severity:
            errors = [e for e in errors if e.severity == severity]
        if error_type:
            errors = [e for e in errors if e.error_type == error_type]
        if since:
            errors = [e for e in errors if e.timestamp >= since]

        return errors[-limit:]

    def get_error_stats(self) -> Dict[str, Any]:
        """获取错误统计"""
        with self._lock:
            errors = list(self._errors)

        now = datetime.now()
        last_hour = now - timedelta(hours=1)
        last_day = now - timedelta(days=1)

        hourly_errors = [e for e in errors if e.timestamp >= last_hour]
        daily_errors = [e for e in errors if e.timestamp >= last_day]

        severity_counts = {}
        for sev in ErrorSeverity:
            severity_counts[sev.value] = len([e for e in errors if e.severity == sev])

        return {
            "total_errors": len(errors),
            "errors_last_hour": len(hourly_errors),
            "errors_last_day": len(daily_errors),
            "by_severity": severity_counts,
            "top_error_types": dict(sorted(
                self._error_counts.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10]),
            "unresolved_count": len([e for e in errors if not e.resolved])
        }

    def resolve_error(self, error_id: str) -> bool:
        """标记错误已解决"""
        with self._lock:
            for error in self._errors:
                if error.error_id == error_id:
                    error.resolved = True
                    error.resolution_time = datetime.now()
                    return True
        return False

    def clear_resolved(self):
        """清除已解决的错误"""
        with self._lock:
            self._errors = deque(
                [e for e in self._errors if not e.resolved],
                maxlen=self.max_errors
            )

    def export_errors(self, filepath: str, format: str = "json") -> str:
        """导出错误记录"""
        with self._lock:
            errors = [e.to_dict() for e in self._errors]

        if format == "json":
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(errors, f, indent=2, ensure_ascii=False)
        elif format == "csv":
            import csv
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                if errors:
                    writer = csv.DictWriter(f, fieldnames=errors[0].keys())
                    writer.writeheader()
                    writer.writerows(errors)

        return filepath


# 全局错误跟踪器
_error_tracker: Optional[ErrorTracker] = None


def get_error_tracker() -> ErrorTracker:
    """获取全局错误跟踪器"""
    global _error_tracker
    if _error_tracker is None:
        _error_tracker = ErrorTracker()
    return _error_tracker


def track_error(message: str, **kwargs) -> ErrorRecord:
    """快捷跟踪错误"""
    return get_error_tracker().track_error(message, **kwargs)


def track_exception(exception: Exception, **kwargs) -> ErrorRecord:
    """快捷跟踪异常"""
    return get_error_tracker().track_exception(exception, **kwargs)
