# -*- coding: utf-8 -*-
"""
Prometheus 指标导出器
提供交易系统的实时监控指标
"""

import logging
import os
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Any, Dict, Optional
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class TradingMetrics:
    """交易指标"""
    # 资产指标
    total_equity: float = 0.0
    cash: float = 0.0
    position_value: float = 0.0

    # 盈亏指标
    total_pnl: float = 0.0
    daily_pnl: float = 0.0
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0

    # 收益率指标
    total_return: float = 0.0
    daily_return: float = 0.0
    sharpe_ratio: float = 0.0

    # 风险指标
    current_drawdown: float = 0.0
    max_drawdown: float = 0.0
    volatility: float = 0.0

    # 交易指标
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    avg_slippage: float = 0.0

    # 订单指标
    pending_orders: int = 0
    filled_orders: int = 0
    cancelled_orders: int = 0
    rejected_orders: int = 0
    fill_rate: float = 0.0

    # 延迟指标
    avg_order_latency_ms: float = 0.0
    p99_order_latency_ms: float = 0.0

    # 系统状态
    circuit_breaker_status: str = "closed"
    risk_level: str = "low"
    is_trading: bool = True

    # 时间戳
    last_update: str = ""


class MetricsExporter:
    """
    Prometheus 指标导出器
    """

    def __init__(self, port: int = 9090):
        self.port = port
        self._metrics = TradingMetrics()
        self._lock = threading.Lock()
        self._server: Optional[HTTPServer] = None
        self._server_thread: Optional[threading.Thread] = None

    def update_metrics(self, **kwargs):
        """更新指标"""
        with self._lock:
            for key, value in kwargs.items():
                if hasattr(self._metrics, key):
                    setattr(self._metrics, key, value)
            self._metrics.last_update = datetime.now().isoformat()

    def get_metrics(self) -> TradingMetrics:
        """获取指标"""
        with self._lock:
            return self._metrics

    def generate_prometheus_format(self) -> str:
        """生成 Prometheus 格式的指标"""
        lines = []
        metrics = self.get_metrics()

        # 资产指标
        lines.append(f'# HELP ai_trader_equity Total equity in USD')
        lines.append(f'# TYPE ai_trader_equity gauge')
        lines.append(f'ai_trader_equity {metrics.total_equity}')

        lines.append(f'ai_trader_cash {metrics.cash}')
        lines.append(f'ai_trader_position_value {metrics.position_value}')

        # 盈亏指标
        lines.append(f'# HELP ai_trader_pnl Profit and loss')
        lines.append(f'# TYPE ai_trader_pnl gauge')
        lines.append(f'ai_trader_total_pnl {metrics.total_pnl}')
        lines.append(f'ai_trader_daily_pnl {metrics.daily_pnl}')
        lines.append(f'ai_trader_unrealized_pnl {metrics.unrealized_pnl}')
        lines.append(f'ai_trader_realized_pnl {metrics.realized_pnl}')

        # 收益率指标
        lines.append(f'# HELP ai_trader_return Return rate')
        lines.append(f'# TYPE ai_trader_return gauge')
        lines.append(f'ai_trader_total_return {metrics.total_return}')
        lines.append(f'ai_trader_daily_return {metrics.daily_return}')
        lines.append(f'ai_trader_sharpe_ratio {metrics.sharpe_ratio}')

        # 风险指标
        lines.append(f'# HELP ai_trader_drawdown Drawdown metrics')
        lines.append(f'# TYPE ai_trader_drawdown gauge')
        lines.append(f'ai_trader_current_drawdown {metrics.current_drawdown}')
        lines.append(f'ai_trader_max_drawdown {metrics.max_drawdown}')
        lines.append(f'ai_trader_volatility {metrics.volatility}')

        # 交易指标
        lines.append(f'# HELP ai_trader_trades Trade statistics')
        lines.append(f'# TYPE ai_trader_trades counter')
        lines.append(f'ai_trader_total_trades {metrics.total_trades}')
        lines.append(f'ai_trader_winning_trades {metrics.winning_trades}')
        lines.append(f'ai_trader_losing_trades {metrics.losing_trades}')
        lines.append(f'ai_trader_win_rate {metrics.win_rate}')
        lines.append(f'ai_trader_avg_slippage {metrics.avg_slippage}')

        # 订单指标
        lines.append(f'# HELP ai_trader_orders Order statistics')
        lines.append(f'# TYPE ai_trader_orders gauge')
        lines.append(f'ai_trader_pending_orders {metrics.pending_orders}')
        lines.append(f'ai_trader_filled_orders {metrics.filled_orders}')
        lines.append(f'ai_trader_cancelled_orders {metrics.cancelled_orders}')
        lines.append(f'ai_trader_rejected_orders {metrics.rejected_orders}')
        lines.append(f'ai_trader_fill_rate {metrics.fill_rate}')

        # 延迟指标
        lines.append(f'# HELP ai_trader_latency Order latency in milliseconds')
        lines.append(f'# TYPE ai_trader_latency gauge')
        lines.append(f'ai_trader_avg_order_latency_ms {metrics.avg_order_latency_ms}')
        lines.append(f'ai_trader_p99_order_latency_ms {metrics.p99_order_latency_ms}')

        # 系统状态
        cb_value = 1 if metrics.circuit_breaker_status == "open" else 0
        lines.append(f'ai_trader_circuit_breaker_open {cb_value}')

        risk_values = {"low": 0, "medium": 1, "high": 2, "critical": 3, "halted": 4}
        lines.append(f'ai_trader_risk_level {risk_values.get(metrics.risk_level, 0)}')

        trading_value = 1 if metrics.is_trading else 0
        lines.append(f'ai_trader_is_trading {trading_value}')

        return '\n'.join(lines)

    def generate_json_format(self) -> str:
        """生成 JSON 格式的指标"""
        metrics = self.get_metrics()
        return json.dumps(metrics.__dict__, indent=2)

    def start_server(self):
        """启动 HTTP 服务器"""
        exporter = self

        class MetricsHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path == '/metrics':
                    content = exporter.generate_prometheus_format()
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/plain; charset=utf-8')
                    self.end_headers()
                    self.wfile.write(content.encode())
                elif self.path == '/json':
                    content = exporter.generate_json_format()
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(content.encode())
                elif self.path == '/health':
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(b'{"status": "healthy"}')
                else:
                    self.send_response(404)
                    self.end_headers()

            def log_message(self, format, *args):
                pass  # 禁用访问日志

        self._server = HTTPServer(('0.0.0.0', self.port), MetricsHandler)
        self._server_thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._server_thread.start()
        logger.info(f"Metrics server started on port {self.port}")

    def stop_server(self):
        """停止服务器"""
        if self._server:
            self._server.shutdown()
            self._server = None
        logger.info("Metrics server stopped")


# 全局单例
_metrics_exporter: Optional[MetricsExporter] = None


def get_metrics_exporter(port: int = 9090) -> MetricsExporter:
    """获取指标导出器单例"""
    global _metrics_exporter
    if _metrics_exporter is None:
        _metrics_exporter = MetricsExporter(port)
    return _metrics_exporter


def start_metrics_server(port: int = 9090) -> MetricsExporter:
    """启动指标服务器"""
    exporter = get_metrics_exporter(port)
    exporter.start_server()
    return exporter
