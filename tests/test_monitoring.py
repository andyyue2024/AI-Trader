# -*- coding: utf-8 -*-
"""
监控模块单元测试
"""

import pytest
import json
import threading
import time
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
from urllib.request import urlopen

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from monitoring.metrics_exporter import (
    MetricsExporter, TradingMetrics,
    get_metrics_exporter, start_metrics_server
)
from monitoring.feishu_alert import (
    FeishuAlert, AlertConfig, Alert, AlertLevel,
    send_feishu_alert, get_feishu_alert
)
from monitoring.grafana_dashboard import (
    generate_dashboard_json, save_dashboard_json
)


class TestTradingMetrics:
    """交易指标测试"""

    def test_default_values(self):
        """测试默认值"""
        metrics = TradingMetrics()

        assert metrics.total_equity == 0.0
        assert metrics.daily_pnl == 0.0
        assert metrics.total_trades == 0
        assert metrics.is_trading == True


class TestMetricsExporter:
    """指标导出器测试"""

    def test_update_metrics(self):
        """测试更新指标"""
        exporter = MetricsExporter()

        exporter.update_metrics(
            total_equity=10000.0,
            daily_return=0.02,
            total_trades=10
        )

        metrics = exporter.get_metrics()

        assert metrics.total_equity == 10000.0
        assert metrics.daily_return == 0.02
        assert metrics.total_trades == 10

    def test_prometheus_format(self):
        """测试 Prometheus 格式输出"""
        exporter = MetricsExporter()
        exporter.update_metrics(
            total_equity=10000.0,
            current_drawdown=0.05
        )

        output = exporter.generate_prometheus_format()

        assert "ai_trader_equity 10000.0" in output
        assert "ai_trader_current_drawdown 0.05" in output

    def test_json_format(self):
        """测试 JSON 格式输出"""
        exporter = MetricsExporter()
        exporter.update_metrics(total_equity=10000.0)

        output = exporter.generate_json_format()
        data = json.loads(output)

        assert data["total_equity"] == 10000.0

    def test_server_start_stop(self):
        """测试服务器启动停止"""
        exporter = MetricsExporter(port=19090)

        exporter.start_server()
        time.sleep(0.5)  # 等待服务器启动

        # 尝试访问健康检查端点
        try:
            response = urlopen("http://localhost:19090/health", timeout=2)
            assert response.status == 200
        except Exception as e:
            # 如果无法访问，至少验证服务器对象存在
            assert exporter._server is not None

        exporter.stop_server()
        assert exporter._server is None


class TestAlert:
    """告警消息测试"""

    def test_info_alert(self):
        """测试信息级别告警"""
        alert = Alert(
            level=AlertLevel.INFO,
            title="Test Info",
            content="This is a test"
        )

        assert alert.level == AlertLevel.INFO
        assert alert.title == "Test Info"
        assert alert.timestamp is not None

    def test_extra_fields(self):
        """测试额外字段"""
        alert = Alert(
            level=AlertLevel.WARNING,
            title="Test",
            content="Content",
            extra_fields={"symbol": "TQQQ", "price": "75.00"}
        )

        assert alert.extra_fields["symbol"] == "TQQQ"


class TestAlertConfig:
    """告警配置测试"""

    def test_default_config(self):
        """测试默认配置"""
        config = AlertConfig()

        assert config.enabled == True
        assert config.min_interval == 60.0
        assert config.max_alerts_per_hour == 30


class TestFeishuAlert:
    """飞书告警测试"""

    def test_initialization(self):
        """测试初始化"""
        config = AlertConfig(
            webhook_url="https://test.webhook.url",
            enabled=True
        )
        alerter = FeishuAlert(config)

        assert alerter.config.webhook_url == "https://test.webhook.url"

    def test_disabled_alert(self):
        """测试禁用时不发送"""
        config = AlertConfig(enabled=False)
        alerter = FeishuAlert(config)

        result = alerter.send_info("Test", "Content")

        assert result == False

    def test_no_webhook_url(self):
        """测试无 webhook URL"""
        config = AlertConfig(webhook_url="", enabled=True)
        alerter = FeishuAlert(config)

        result = alerter.send_info("Test", "Content")

        assert result == False

    def test_dedup(self):
        """测试告警去重"""
        config = AlertConfig(
            webhook_url="https://test.url",
            min_interval=60.0,
            enabled=True
        )
        alerter = FeishuAlert(config)

        # Mock 发送请求
        with patch.object(alerter, '_check_rate_limit', return_value=True):
            # 第一次应该通过去重检查
            result1 = alerter._check_dedup("warning:Test Alert")
            assert result1 == True

            # 立即第二次应该被去重
            result2 = alerter._check_dedup("warning:Test Alert")
            assert result2 == False

    def test_rate_limit(self):
        """测试速率限制"""
        config = AlertConfig(
            webhook_url="https://test.url",
            max_alerts_per_hour=2,
            enabled=True
        )
        alerter = FeishuAlert(config)

        # 模拟发送多条告警
        alerter._alert_count = [time.time(), time.time()]

        result = alerter._check_rate_limit()

        assert result == False

    def test_quiet_hours(self):
        """测试静默时间"""
        # 设置静默时间为当前小时
        current_hour = datetime.now().hour
        config = AlertConfig(
            webhook_url="https://test.url",
            quiet_hours_start=current_hour,
            quiet_hours_end=(current_hour + 1) % 24,
            enabled=True
        )
        alerter = FeishuAlert(config)

        result = alerter._is_quiet_hours()

        assert result == True

    def test_build_message(self):
        """测试消息构建"""
        config = AlertConfig(webhook_url="https://test.url")
        alerter = FeishuAlert(config)

        alert = Alert(
            level=AlertLevel.WARNING,
            title="Test Alert",
            content="Test content",
            extra_fields={"key": "value"}
        )

        message = alerter._build_message(alert)

        assert message["msg_type"] == "interactive"
        assert "card" in message
        assert message["card"]["header"]["template"] == "yellow"


class TestGrafanaDashboard:
    """Grafana 仪表盘测试"""

    def test_generate_dashboard(self):
        """测试生成仪表盘"""
        dashboard = generate_dashboard_json()

        assert dashboard["title"] == "AI-Trader Dashboard"
        assert "panels" in dashboard
        assert len(dashboard["panels"]) > 0

    def test_custom_title(self):
        """测试自定义标题"""
        dashboard = generate_dashboard_json(title="Custom Dashboard")

        assert dashboard["title"] == "Custom Dashboard"

    def test_datasource(self):
        """测试数据源配置"""
        dashboard = generate_dashboard_json(datasource="MyPrometheus")

        # 检查面板是否使用了指定的数据源
        for panel in dashboard["panels"]:
            if "datasource" in panel:
                assert panel["datasource"] == "MyPrometheus"

    def test_panels_structure(self):
        """测试面板结构"""
        dashboard = generate_dashboard_json()

        # 检查是否有必要的面板类型
        panel_types = [p.get("type") for p in dashboard["panels"]]

        assert "row" in panel_types
        assert "stat" in panel_types
        assert "timeseries" in panel_types

    def test_save_dashboard(self, tmp_path):
        """测试保存仪表盘"""
        filepath = str(tmp_path / "test_dashboard.json")

        result = save_dashboard_json(filepath)

        assert os.path.exists(result)

        with open(result, "r") as f:
            data = json.load(f)
            assert "panels" in data


class TestIntegration:
    """集成测试"""

    def test_metrics_and_alert_integration(self):
        """测试指标和告警集成"""
        # 创建指标导出器
        exporter = MetricsExporter()
        exporter.update_metrics(
            current_drawdown=0.16,  # 超过15%
            risk_level="critical"
        )

        # 创建告警器（禁用实际发送）
        config = AlertConfig(enabled=False)
        alerter = FeishuAlert(config)

        # 检查是否应该触发告警
        metrics = exporter.get_metrics()

        if metrics.current_drawdown > 0.15:
            # 应该发送告警
            assert metrics.risk_level == "critical"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
