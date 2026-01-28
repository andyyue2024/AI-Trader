# -*- coding: utf-8 -*-
"""
Grafana 仪表盘配置生成器
生成 AI-Trader 监控仪表盘 JSON 配置
"""

import json
from typing import Any, Dict, List


def generate_dashboard_json(
    datasource: str = "Prometheus",
    refresh_interval: str = "5s",
    title: str = "AI-Trader Dashboard"
) -> Dict[str, Any]:
    """
    生成 Grafana 仪表盘 JSON 配置

    Args:
        datasource: Prometheus 数据源名称
        refresh_interval: 刷新间隔
        title: 仪表盘标题

    Returns:
        Dict: Grafana 仪表盘 JSON 配置
    """

    dashboard = {
        "annotations": {
            "list": [
                {
                    "builtIn": 1,
                    "datasource": "-- Grafana --",
                    "enable": True,
                    "hide": True,
                    "iconColor": "rgba(0, 211, 255, 1)",
                    "name": "Annotations & Alerts",
                    "type": "dashboard"
                }
            ]
        },
        "editable": True,
        "gnetId": None,
        "graphTooltip": 0,
        "id": None,
        "links": [],
        "panels": [],
        "refresh": refresh_interval,
        "schemaVersion": 27,
        "style": "dark",
        "tags": ["ai-trader", "trading", "monitoring"],
        "templating": {"list": []},
        "time": {"from": "now-1h", "to": "now"},
        "timepicker": {},
        "timezone": "",
        "title": title,
        "uid": "ai-trader-main",
        "version": 1
    }

    panel_id = 1

    # Row 1: 概览指标
    dashboard["panels"].append({
        "collapsed": False,
        "gridPos": {"h": 1, "w": 24, "x": 0, "y": 0},
        "id": panel_id,
        "panels": [],
        "title": "📊 Overview",
        "type": "row"
    })
    panel_id += 1

    # 总权益
    dashboard["panels"].append({
        "datasource": datasource,
        "fieldConfig": {
            "defaults": {
                "color": {"mode": "thresholds"},
                "mappings": [],
                "thresholds": {
                    "mode": "absolute",
                    "steps": [
                        {"color": "red", "value": None},
                        {"color": "yellow", "value": 8000},
                        {"color": "green", "value": 10000}
                    ]
                },
                "unit": "currencyUSD"
            },
            "overrides": []
        },
        "gridPos": {"h": 4, "w": 4, "x": 0, "y": 1},
        "id": panel_id,
        "options": {
            "colorMode": "value",
            "graphMode": "area",
            "justifyMode": "auto",
            "orientation": "auto",
            "reduceOptions": {
                "calcs": ["lastNotNull"],
                "fields": "",
                "values": False
            },
            "textMode": "auto"
        },
        "pluginVersion": "8.0.0",
        "targets": [
            {
                "expr": "ai_trader_equity",
                "interval": "",
                "legendFormat": "",
                "refId": "A"
            }
        ],
        "title": "Total Equity",
        "type": "stat"
    })
    panel_id += 1

    # 日收益率
    dashboard["panels"].append({
        "datasource": datasource,
        "fieldConfig": {
            "defaults": {
                "color": {"mode": "thresholds"},
                "mappings": [],
                "thresholds": {
                    "mode": "absolute",
                    "steps": [
                        {"color": "red", "value": None},
                        {"color": "yellow", "value": 0},
                        {"color": "green", "value": 0.01}
                    ]
                },
                "unit": "percentunit"
            }
        },
        "gridPos": {"h": 4, "w": 4, "x": 4, "y": 1},
        "id": panel_id,
        "options": {
            "colorMode": "value",
            "graphMode": "area",
            "reduceOptions": {"calcs": ["lastNotNull"]}
        },
        "targets": [
            {"expr": "ai_trader_daily_return", "refId": "A"}
        ],
        "title": "Daily Return",
        "type": "stat"
    })
    panel_id += 1

    # 回撤
    dashboard["panels"].append({
        "datasource": datasource,
        "fieldConfig": {
            "defaults": {
                "color": {"mode": "thresholds"},
                "thresholds": {
                    "steps": [
                        {"color": "green", "value": None},
                        {"color": "yellow", "value": 0.05},
                        {"color": "orange", "value": 0.10},
                        {"color": "red", "value": 0.15}
                    ]
                },
                "unit": "percentunit"
            }
        },
        "gridPos": {"h": 4, "w": 4, "x": 8, "y": 1},
        "id": panel_id,
        "options": {"colorMode": "value", "graphMode": "area"},
        "targets": [
            {"expr": "ai_trader_current_drawdown", "refId": "A"}
        ],
        "title": "Current Drawdown",
        "type": "stat"
    })
    panel_id += 1

    # 风险级别
    dashboard["panels"].append({
        "datasource": datasource,
        "fieldConfig": {
            "defaults": {
                "color": {"mode": "thresholds"},
                "mappings": [
                    {"options": {"0": {"text": "LOW"}}, "type": "value"},
                    {"options": {"1": {"text": "MEDIUM"}}, "type": "value"},
                    {"options": {"2": {"text": "HIGH"}}, "type": "value"},
                    {"options": {"3": {"text": "CRITICAL"}}, "type": "value"},
                    {"options": {"4": {"text": "HALTED"}}, "type": "value"}
                ],
                "thresholds": {
                    "steps": [
                        {"color": "green", "value": None},
                        {"color": "yellow", "value": 1},
                        {"color": "orange", "value": 2},
                        {"color": "red", "value": 3}
                    ]
                }
            }
        },
        "gridPos": {"h": 4, "w": 4, "x": 12, "y": 1},
        "id": panel_id,
        "targets": [
            {"expr": "ai_trader_risk_level", "refId": "A"}
        ],
        "title": "Risk Level",
        "type": "stat"
    })
    panel_id += 1

    # 夏普比率
    dashboard["panels"].append({
        "datasource": datasource,
        "fieldConfig": {
            "defaults": {
                "thresholds": {
                    "steps": [
                        {"color": "red", "value": None},
                        {"color": "yellow", "value": 1},
                        {"color": "green", "value": 2}
                    ]
                }
            }
        },
        "gridPos": {"h": 4, "w": 4, "x": 16, "y": 1},
        "id": panel_id,
        "targets": [
            {"expr": "ai_trader_sharpe_ratio", "refId": "A"}
        ],
        "title": "Sharpe Ratio",
        "type": "stat"
    })
    panel_id += 1

    # 熔断器状态
    dashboard["panels"].append({
        "datasource": datasource,
        "fieldConfig": {
            "defaults": {
                "mappings": [
                    {"options": {"0": {"text": "NORMAL", "color": "green"}}, "type": "value"},
                    {"options": {"1": {"text": "TRIPPED", "color": "red"}}, "type": "value"}
                ]
            }
        },
        "gridPos": {"h": 4, "w": 4, "x": 20, "y": 1},
        "id": panel_id,
        "targets": [
            {"expr": "ai_trader_circuit_breaker_open", "refId": "A"}
        ],
        "title": "Circuit Breaker",
        "type": "stat"
    })
    panel_id += 1

    # Row 2: 权益曲线
    dashboard["panels"].append({
        "collapsed": False,
        "gridPos": {"h": 1, "w": 24, "x": 0, "y": 5},
        "id": panel_id,
        "panels": [],
        "title": "📈 Equity & Performance",
        "type": "row"
    })
    panel_id += 1

    # 权益曲线图
    dashboard["panels"].append({
        "datasource": datasource,
        "fieldConfig": {
            "defaults": {"unit": "currencyUSD"}
        },
        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 6},
        "id": panel_id,
        "options": {
            "legend": {"displayMode": "list", "placement": "bottom"},
            "tooltip": {"mode": "single"}
        },
        "targets": [
            {"expr": "ai_trader_equity", "legendFormat": "Equity", "refId": "A"},
            {"expr": "ai_trader_cash", "legendFormat": "Cash", "refId": "B"},
            {"expr": "ai_trader_position_value", "legendFormat": "Position", "refId": "C"}
        ],
        "title": "Equity Curve",
        "type": "timeseries"
    })
    panel_id += 1

    # PnL 图
    dashboard["panels"].append({
        "datasource": datasource,
        "fieldConfig": {
            "defaults": {"unit": "currencyUSD"}
        },
        "gridPos": {"h": 8, "w": 12, "x": 12, "y": 6},
        "id": panel_id,
        "targets": [
            {"expr": "ai_trader_total_pnl", "legendFormat": "Total PnL", "refId": "A"},
            {"expr": "ai_trader_daily_pnl", "legendFormat": "Daily PnL", "refId": "B"},
            {"expr": "ai_trader_realized_pnl", "legendFormat": "Realized PnL", "refId": "C"}
        ],
        "title": "Profit & Loss",
        "type": "timeseries"
    })
    panel_id += 1

    # Row 3: 交易指标
    dashboard["panels"].append({
        "collapsed": False,
        "gridPos": {"h": 1, "w": 24, "x": 0, "y": 14},
        "id": panel_id,
        "panels": [],
        "title": "📊 Trading Metrics",
        "type": "row"
    })
    panel_id += 1

    # 交易统计
    dashboard["panels"].append({
        "datasource": datasource,
        "gridPos": {"h": 6, "w": 6, "x": 0, "y": 15},
        "id": panel_id,
        "targets": [
            {"expr": "ai_trader_total_trades", "legendFormat": "Total Trades", "refId": "A"},
            {"expr": "ai_trader_winning_trades", "legendFormat": "Winning", "refId": "B"},
            {"expr": "ai_trader_losing_trades", "legendFormat": "Losing", "refId": "C"}
        ],
        "title": "Trade Statistics",
        "type": "timeseries"
    })
    panel_id += 1

    # 胜率
    dashboard["panels"].append({
        "datasource": datasource,
        "fieldConfig": {
            "defaults": {
                "unit": "percentunit",
                "thresholds": {
                    "steps": [
                        {"color": "red", "value": None},
                        {"color": "yellow", "value": 0.4},
                        {"color": "green", "value": 0.5}
                    ]
                }
            }
        },
        "gridPos": {"h": 6, "w": 4, "x": 6, "y": 15},
        "id": panel_id,
        "options": {"orientation": "horizontal"},
        "targets": [
            {"expr": "ai_trader_win_rate", "refId": "A"}
        ],
        "title": "Win Rate",
        "type": "gauge"
    })
    panel_id += 1

    # 成交率
    dashboard["panels"].append({
        "datasource": datasource,
        "fieldConfig": {
            "defaults": {
                "unit": "percentunit",
                "min": 0,
                "max": 1,
                "thresholds": {
                    "steps": [
                        {"color": "red", "value": None},
                        {"color": "yellow", "value": 0.9},
                        {"color": "green", "value": 0.95}
                    ]
                }
            }
        },
        "gridPos": {"h": 6, "w": 4, "x": 10, "y": 15},
        "id": panel_id,
        "targets": [
            {"expr": "ai_trader_fill_rate", "refId": "A"}
        ],
        "title": "Fill Rate (≥95%)",
        "type": "gauge"
    })
    panel_id += 1

    # 滑点
    dashboard["panels"].append({
        "datasource": datasource,
        "fieldConfig": {
            "defaults": {
                "unit": "percentunit",
                "thresholds": {
                    "steps": [
                        {"color": "green", "value": None},
                        {"color": "yellow", "value": 0.001},
                        {"color": "red", "value": 0.002}
                    ]
                }
            }
        },
        "gridPos": {"h": 6, "w": 4, "x": 14, "y": 15},
        "id": panel_id,
        "targets": [
            {"expr": "ai_trader_avg_slippage", "refId": "A"}
        ],
        "title": "Avg Slippage (≤0.2%)",
        "type": "gauge"
    })
    panel_id += 1

    # 延迟
    dashboard["panels"].append({
        "datasource": datasource,
        "fieldConfig": {
            "defaults": {
                "unit": "ms",
                "thresholds": {
                    "steps": [
                        {"color": "green", "value": None},
                        {"color": "yellow", "value": 500},
                        {"color": "red", "value": 1000}
                    ]
                }
            }
        },
        "gridPos": {"h": 6, "w": 6, "x": 18, "y": 15},
        "id": panel_id,
        "targets": [
            {"expr": "ai_trader_avg_order_latency_ms", "legendFormat": "Avg", "refId": "A"},
            {"expr": "ai_trader_p99_order_latency_ms", "legendFormat": "P99", "refId": "B"}
        ],
        "title": "Order Latency",
        "type": "timeseries"
    })
    panel_id += 1

    return dashboard


def save_dashboard_json(filepath: str = "grafana_dashboard.json"):
    """保存仪表盘 JSON 到文件"""
    dashboard = generate_dashboard_json()
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(dashboard, f, indent=2)
    return filepath


if __name__ == "__main__":
    # 生成并保存仪表盘配置
    path = save_dashboard_json()
    print(f"Dashboard JSON saved to: {path}")
