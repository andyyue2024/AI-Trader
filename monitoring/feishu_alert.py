# -*- coding: utf-8 -*-
"""
飞书告警模块
实现异常5分钟内飞书叫醒功能
"""

import asyncio
import hashlib
import hmac
import base64
import json
import logging
import os
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from urllib.request import Request, urlopen
from urllib.error import URLError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AlertLevel(Enum):
    """告警级别"""
    INFO = "info"           # 信息
    WARNING = "warning"     # 警告
    ERROR = "error"         # 错误
    CRITICAL = "critical"   # 严重


@dataclass
class AlertConfig:
    """告警配置"""
    webhook_url: str = ""
    secret: str = ""
    enabled: bool = True
    min_interval: float = 60.0        # 同类告警最小间隔(秒)
    max_alerts_per_hour: int = 30     # 每小时最大告警数
    quiet_hours_start: int = -1       # 静默开始时间 (-1表示不启用)
    quiet_hours_end: int = -1         # 静默结束时间


@dataclass
class Alert:
    """告警消息"""
    level: AlertLevel
    title: str
    content: str
    timestamp: datetime = None
    extra_fields: Dict[str, str] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.extra_fields is None:
            self.extra_fields = {}


class FeishuAlert:
    """
    飞书告警器
    支持 Webhook 推送告警消息
    """

    def __init__(self, config: Optional[AlertConfig] = None):
        self.config = config or AlertConfig(
            webhook_url=os.getenv("FEISHU_WEBHOOK_URL", ""),
            secret=os.getenv("FEISHU_WEBHOOK_SECRET", "")
        )

        self._alert_history: Dict[str, float] = {}  # 告警去重
        self._alert_count: List[float] = []         # 告警计数
        self._lock = threading.Lock()

    def _generate_sign(self, timestamp: int) -> str:
        """生成签名"""
        if not self.config.secret:
            return ""

        string_to_sign = f"{timestamp}\n{self.config.secret}"
        hmac_code = hmac.new(
            string_to_sign.encode("utf-8"),
            digestmod=hashlib.sha256
        ).digest()
        sign = base64.b64encode(hmac_code).decode("utf-8")
        return sign

    def _check_rate_limit(self) -> bool:
        """检查速率限制"""
        with self._lock:
            now = time.time()

            # 清理超过1小时的记录
            self._alert_count = [t for t in self._alert_count if now - t < 3600]

            if len(self._alert_count) >= self.config.max_alerts_per_hour:
                return False

            return True

    def _check_dedup(self, alert_key: str) -> bool:
        """检查去重"""
        with self._lock:
            now = time.time()

            if alert_key in self._alert_history:
                last_time = self._alert_history[alert_key]
                if now - last_time < self.config.min_interval:
                    return False

            self._alert_history[alert_key] = now
            return True

    def _is_quiet_hours(self) -> bool:
        """检查是否在静默时间"""
        if self.config.quiet_hours_start < 0:
            return False

        hour = datetime.now().hour
        start = self.config.quiet_hours_start
        end = self.config.quiet_hours_end

        if start <= end:
            return start <= hour < end
        else:  # 跨午夜
            return hour >= start or hour < end

    def _build_message(self, alert: Alert) -> Dict[str, Any]:
        """构建消息体"""
        # 颜色映射
        colors = {
            AlertLevel.INFO: "green",
            AlertLevel.WARNING: "yellow",
            AlertLevel.ERROR: "orange",
            AlertLevel.CRITICAL: "red"
        }

        # 图标映射
        icons = {
            AlertLevel.INFO: "ℹ️",
            AlertLevel.WARNING: "⚠️",
            AlertLevel.ERROR: "❌",
            AlertLevel.CRITICAL: "🚨"
        }

        # 构建卡片消息
        elements = [
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": alert.content
                }
            }
        ]

        # 添加额外字段
        if alert.extra_fields:
            fields = []
            for key, value in alert.extra_fields.items():
                fields.append({
                    "is_short": True,
                    "text": {
                        "tag": "lark_md",
                        "content": f"**{key}:** {value}"
                    }
                })
            elements.append({
                "tag": "div",
                "fields": fields
            })

        # 添加时间戳
        elements.append({
            "tag": "note",
            "elements": [
                {
                    "tag": "plain_text",
                    "content": f"时间: {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
                }
            ]
        })

        card = {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {
                        "tag": "plain_text",
                        "content": f"{icons[alert.level]} {alert.title}"
                    },
                    "template": colors[alert.level]
                },
                "elements": elements
            }
        }

        return card

    def send(self, alert: Alert) -> bool:
        """
        发送告警

        Args:
            alert: 告警消息

        Returns:
            bool: 是否发送成功
        """
        if not self.config.enabled:
            logger.debug("Alert is disabled")
            return False

        if not self.config.webhook_url:
            logger.warning("Feishu webhook URL not configured")
            return False

        # 检查静默时间
        if self._is_quiet_hours() and alert.level != AlertLevel.CRITICAL:
            logger.debug("In quiet hours, skipping non-critical alert")
            return False

        # 检查速率限制
        if not self._check_rate_limit():
            logger.warning("Alert rate limit exceeded")
            return False

        # 检查去重
        alert_key = f"{alert.level.value}:{alert.title}"
        if not self._check_dedup(alert_key):
            logger.debug(f"Duplicate alert suppressed: {alert_key}")
            return False

        try:
            # 构建消息
            message = self._build_message(alert)

            # 添加签名
            timestamp = int(time.time())
            if self.config.secret:
                sign = self._generate_sign(timestamp)
                message["timestamp"] = str(timestamp)
                message["sign"] = sign

            # 发送请求
            data = json.dumps(message).encode("utf-8")
            req = Request(
                self.config.webhook_url,
                data=data,
                headers={"Content-Type": "application/json"}
            )

            with urlopen(req, timeout=10) as response:
                result = json.loads(response.read().decode())

                if result.get("code") == 0 or result.get("StatusCode") == 0:
                    logger.info(f"Alert sent: {alert.title}")
                    with self._lock:
                        self._alert_count.append(time.time())
                    return True
                else:
                    logger.error(f"Alert send failed: {result}")
                    return False

        except URLError as e:
            logger.error(f"Alert send error: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending alert: {e}")
            return False

    def send_info(self, title: str, content: str, **extra_fields) -> bool:
        """发送信息"""
        return self.send(Alert(
            level=AlertLevel.INFO,
            title=title,
            content=content,
            extra_fields=extra_fields
        ))

    def send_warning(self, title: str, content: str, **extra_fields) -> bool:
        """发送警告"""
        return self.send(Alert(
            level=AlertLevel.WARNING,
            title=title,
            content=content,
            extra_fields=extra_fields
        ))

    def send_error(self, title: str, content: str, **extra_fields) -> bool:
        """发送错误"""
        return self.send(Alert(
            level=AlertLevel.ERROR,
            title=title,
            content=content,
            extra_fields=extra_fields
        ))

    def send_critical(self, title: str, content: str, **extra_fields) -> bool:
        """发送严重告警"""
        return self.send(Alert(
            level=AlertLevel.CRITICAL,
            title=title,
            content=content,
            extra_fields=extra_fields
        ))


# 全局单例
_feishu_alert: Optional[FeishuAlert] = None


def get_feishu_alert(config: Optional[AlertConfig] = None) -> FeishuAlert:
    """获取飞书告警器单例"""
    global _feishu_alert
    if _feishu_alert is None:
        _feishu_alert = FeishuAlert(config)
    return _feishu_alert


def send_feishu_alert(
    title: str,
    content: str,
    level: AlertLevel = AlertLevel.WARNING,
    **extra_fields
) -> bool:
    """快速发送飞书告警"""
    alerter = get_feishu_alert()
    return alerter.send(Alert(
        level=level,
        title=title,
        content=content,
        extra_fields=extra_fields
    ))
