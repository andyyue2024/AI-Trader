# -*- coding: utf-8 -*-
"""
AI-Trader Web UI
基于 FastAPI 的 Web 仪表盘界面
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
    from fastapi.staticfiles import StaticFiles
    import uvicorn
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# 创建 FastAPI 应用
if FASTAPI_AVAILABLE:
    app = FastAPI(
        title="AI-Trader Dashboard",
        description="High Frequency Trading System Dashboard",
        version="1.0.0"
    )

    # CORS 配置
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    app = None


# WebSocket 连接管理
class ConnectionManager:
    """WebSocket 连接管理器"""

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        """广播消息到所有连接"""
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                pass


manager = ConnectionManager()


# 全局状态存储
class DashboardState:
    """仪表盘状态"""

    def __init__(self):
        self.trader = None
        self.is_running = False
        self.symbols = []
        self.last_update = None
        self.trades_history = []
        self.alerts = []

    def update(self, data: Dict[str, Any]):
        self.last_update = datetime.now()
        for key, value in data.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_running": self.is_running,
            "symbols": self.symbols,
            "last_update": self.last_update.isoformat() if self.last_update else None,
            "trades_count": len(self.trades_history),
            "alerts_count": len(self.alerts)
        }


dashboard_state = DashboardState()


# HTML 模板
DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI-Trader Dashboard</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        .card { @apply bg-white rounded-lg shadow-lg p-6; }
        .stat-value { @apply text-3xl font-bold text-gray-800; }
        .stat-label { @apply text-sm text-gray-500; }
        .status-running { @apply bg-green-500; }
        .status-stopped { @apply bg-red-500; }
        .alert-critical { @apply bg-red-100 border-red-500 text-red-700; }
        .alert-warning { @apply bg-yellow-100 border-yellow-500 text-yellow-700; }
        .alert-info { @apply bg-blue-100 border-blue-500 text-blue-700; }
    </style>
</head>
<body class="bg-gray-100 min-h-screen">
    <nav class="bg-gray-800 text-white p-4">
        <div class="container mx-auto flex justify-between items-center">
            <h1 class="text-2xl font-bold">🚀 AI-Trader Dashboard</h1>
            <div class="flex items-center space-x-4">
                <span id="status-badge" class="px-3 py-1 rounded-full text-sm status-stopped">Stopped</span>
                <span id="last-update" class="text-sm text-gray-300">--</span>
            </div>
        </div>
    </nav>

    <main class="container mx-auto p-6">
        <!-- 统计卡片 -->
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-6">
            <div class="card">
                <div class="stat-label">Total Equity</div>
                <div class="stat-value" id="total-equity">$0.00</div>
                <div class="text-sm text-green-500" id="daily-return">+0.00%</div>
            </div>
            <div class="card">
                <div class="stat-label">Today's P&L</div>
                <div class="stat-value" id="daily-pnl">$0.00</div>
                <div class="text-sm text-gray-500" id="trade-count">0 trades</div>
            </div>
            <div class="card">
                <div class="stat-label">Sharpe Ratio</div>
                <div class="stat-value" id="sharpe-ratio">0.00</div>
                <div class="text-sm" id="sharpe-target">Target: ≥2.0</div>
            </div>
            <div class="card">
                <div class="stat-label">Max Drawdown</div>
                <div class="stat-value" id="max-drawdown">0.00%</div>
                <div class="text-sm" id="drawdown-target">Target: ≤15%</div>
            </div>
        </div>

        <!-- 性能指标 -->
        <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
            <div class="card">
                <div class="stat-label">Fill Rate</div>
                <div class="stat-value" id="fill-rate">0.00%</div>
                <div class="text-sm" id="fill-target">Target: ≥95%</div>
            </div>
            <div class="card">
                <div class="stat-label">Avg Slippage</div>
                <div class="stat-value" id="avg-slippage">0.00%</div>
                <div class="text-sm" id="slippage-target">Target: ≤0.2%</div>
            </div>
            <div class="card">
                <div class="stat-label">Daily Volume</div>
                <div class="stat-value" id="daily-volume">$0</div>
                <div class="text-sm" id="volume-target">Target: ≥$50k</div>
            </div>
        </div>

        <!-- 图表区域 -->
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
            <div class="card">
                <h3 class="text-lg font-semibold mb-4">Equity Curve</h3>
                <canvas id="equity-chart" height="200"></canvas>
            </div>
            <div class="card">
                <h3 class="text-lg font-semibold mb-4">P&L Distribution</h3>
                <canvas id="pnl-chart" height="200"></canvas>
            </div>
        </div>

        <!-- 持仓和交易 -->
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
            <div class="card">
                <h3 class="text-lg font-semibold mb-4">Current Positions</h3>
                <table class="w-full">
                    <thead>
                        <tr class="text-left text-gray-500 text-sm">
                            <th class="pb-2">Symbol</th>
                            <th class="pb-2">Qty</th>
                            <th class="pb-2">Avg Cost</th>
                            <th class="pb-2">P&L</th>
                        </tr>
                    </thead>
                    <tbody id="positions-table">
                        <tr><td colspan="4" class="text-center text-gray-400 py-4">No positions</td></tr>
                    </tbody>
                </table>
            </div>
            <div class="card">
                <h3 class="text-lg font-semibold mb-4">Recent Trades</h3>
                <div id="trades-list" class="space-y-2 max-h-64 overflow-y-auto">
                    <div class="text-center text-gray-400 py-4">No trades yet</div>
                </div>
            </div>
        </div>

        <!-- 告警区域 -->
        <div class="card mb-6">
            <h3 class="text-lg font-semibold mb-4">Alerts</h3>
            <div id="alerts-list" class="space-y-2">
                <div class="text-center text-gray-400 py-4">No alerts</div>
            </div>
        </div>

        <!-- 控制面板 -->
        <div class="card">
            <h3 class="text-lg font-semibold mb-4">Control Panel</h3>
            <div class="flex space-x-4">
                <button id="btn-start" onclick="startTrading()" 
                    class="px-6 py-2 bg-green-500 text-white rounded hover:bg-green-600">
                    Start Trading
                </button>
                <button id="btn-stop" onclick="stopTrading()" 
                    class="px-6 py-2 bg-red-500 text-white rounded hover:bg-red-600">
                    Stop Trading
                </button>
                <button onclick="generateReport()" 
                    class="px-6 py-2 bg-blue-500 text-white rounded hover:bg-blue-600">
                    Generate Report
                </button>
                <button onclick="location.reload()" 
                    class="px-6 py-2 bg-gray-500 text-white rounded hover:bg-gray-600">
                    Refresh
                </button>
            </div>
        </div>
    </main>

    <script>
        let ws;
        let equityChart, pnlChart;

        // 初始化 WebSocket
        function initWebSocket() {
            const wsUrl = `ws://${window.location.host}/ws`;
            ws = new WebSocket(wsUrl);
            
            ws.onopen = () => console.log('WebSocket connected');
            ws.onclose = () => setTimeout(initWebSocket, 3000);
            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                updateDashboard(data);
            };
        }

        // 更新仪表盘
        function updateDashboard(data) {
            if (data.status) {
                const badge = document.getElementById('status-badge');
                badge.textContent = data.status.is_running ? 'Running' : 'Stopped';
                badge.className = data.status.is_running ? 
                    'px-3 py-1 rounded-full text-sm status-running' : 
                    'px-3 py-1 rounded-full text-sm status-stopped';
            }
            
            if (data.metrics) {
                updateMetrics(data.metrics);
            }
            
            if (data.positions) {
                updatePositions(data.positions);
            }
            
            if (data.trades) {
                updateTrades(data.trades);
            }
            
            if (data.alerts) {
                updateAlerts(data.alerts);
            }
            
            document.getElementById('last-update').textContent = 
                'Updated: ' + new Date().toLocaleTimeString();
        }

        function updateMetrics(m) {
            document.getElementById('total-equity').textContent = '$' + (m.total_equity || 0).toLocaleString();
            document.getElementById('daily-return').textContent = ((m.daily_return || 0) * 100).toFixed(2) + '%';
            document.getElementById('daily-pnl').textContent = '$' + (m.daily_pnl || 0).toFixed(2);
            document.getElementById('trade-count').textContent = (m.total_trades || 0) + ' trades';
            document.getElementById('sharpe-ratio').textContent = (m.sharpe_ratio || 0).toFixed(2);
            document.getElementById('max-drawdown').textContent = ((m.max_drawdown || 0) * 100).toFixed(2) + '%';
            document.getElementById('fill-rate').textContent = ((m.fill_rate || 0) * 100).toFixed(2) + '%';
            document.getElementById('avg-slippage').textContent = ((m.avg_slippage || 0) * 100).toFixed(4) + '%';
            document.getElementById('daily-volume').textContent = '$' + (m.daily_volume || 0).toLocaleString();
        }

        function updatePositions(positions) {
            const tbody = document.getElementById('positions-table');
            if (!positions || positions.length === 0) {
                tbody.innerHTML = '<tr><td colspan="4" class="text-center text-gray-400 py-4">No positions</td></tr>';
                return;
            }
            tbody.innerHTML = positions.map(p => `
                <tr class="border-b">
                    <td class="py-2 font-medium">${p.symbol}</td>
                    <td class="py-2">${p.quantity}</td>
                    <td class="py-2">$${p.avg_cost.toFixed(2)}</td>
                    <td class="py-2 ${p.pnl >= 0 ? 'text-green-500' : 'text-red-500'}">
                        ${p.pnl >= 0 ? '+' : ''}$${p.pnl.toFixed(2)}
                    </td>
                </tr>
            `).join('');
        }

        function updateTrades(trades) {
            const container = document.getElementById('trades-list');
            if (!trades || trades.length === 0) {
                container.innerHTML = '<div class="text-center text-gray-400 py-4">No trades yet</div>';
                return;
            }
            container.innerHTML = trades.slice(0, 10).map(t => `
                <div class="flex justify-between items-center p-2 bg-gray-50 rounded">
                    <span class="font-medium">${t.symbol}</span>
                    <span class="${t.side === 'long' ? 'text-green-500' : 'text-red-500'}">${t.side.toUpperCase()}</span>
                    <span>${t.quantity} @ $${t.price.toFixed(2)}</span>
                    <span class="text-sm text-gray-500">${new Date(t.timestamp).toLocaleTimeString()}</span>
                </div>
            `).join('');
        }

        function updateAlerts(alerts) {
            const container = document.getElementById('alerts-list');
            if (!alerts || alerts.length === 0) {
                container.innerHTML = '<div class="text-center text-gray-400 py-4">No alerts</div>';
                return;
            }
            container.innerHTML = alerts.slice(0, 5).map(a => `
                <div class="p-3 border-l-4 rounded alert-${a.level}">
                    <div class="font-medium">${a.title}</div>
                    <div class="text-sm">${a.content}</div>
                    <div class="text-xs mt-1">${new Date(a.timestamp).toLocaleString()}</div>
                </div>
            `).join('');
        }

        async function startTrading() {
            try {
                const response = await fetch('/api/trading/start', { method: 'POST' });
                const data = await response.json();
                alert(data.message || 'Trading started');
            } catch (e) {
                alert('Failed to start trading: ' + e.message);
            }
        }

        async function stopTrading() {
            try {
                const response = await fetch('/api/trading/stop', { method: 'POST' });
                const data = await response.json();
                alert(data.message || 'Trading stopped');
            } catch (e) {
                alert('Failed to stop trading: ' + e.message);
            }
        }

        async function generateReport() {
            try {
                window.open('/api/reports/generate?format=pdf', '_blank');
            } catch (e) {
                alert('Failed to generate report: ' + e.message);
            }
        }

        // 初始化图表
        function initCharts() {
            const equityCtx = document.getElementById('equity-chart').getContext('2d');
            equityChart = new Chart(equityCtx, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [{
                        label: 'Equity',
                        data: [],
                        borderColor: 'rgb(59, 130, 246)',
                        backgroundColor: 'rgba(59, 130, 246, 0.1)',
                        fill: true
                    }]
                },
                options: { responsive: true, maintainAspectRatio: false }
            });

            const pnlCtx = document.getElementById('pnl-chart').getContext('2d');
            pnlChart = new Chart(pnlCtx, {
                type: 'bar',
                data: {
                    labels: [],
                    datasets: [{
                        label: 'Daily P&L',
                        data: [],
                        backgroundColor: []
                    }]
                },
                options: { responsive: true, maintainAspectRatio: false }
            });
        }

        // 加载初始数据
        async function loadInitialData() {
            try {
                const response = await fetch('/api/status');
                const data = await response.json();
                updateDashboard(data);
            } catch (e) {
                console.error('Failed to load initial data:', e);
            }
        }

        // 页面加载
        document.addEventListener('DOMContentLoaded', () => {
            initCharts();
            loadInitialData();
            initWebSocket();
        });
    </script>
</body>
</html>
"""


if FASTAPI_AVAILABLE:
    @app.get("/", response_class=HTMLResponse)
    async def root():
        """主页"""
        return DASHBOARD_HTML

    @app.get("/api/status")
    async def get_status():
        """获取系统状态"""
        return {
            "status": dashboard_state.to_dict(),
            "metrics": {},
            "positions": [],
            "trades": [],
            "alerts": []
        }

    @app.post("/api/trading/start")
    async def start_trading():
        """启动交易"""
        dashboard_state.is_running = True
        await manager.broadcast({"status": dashboard_state.to_dict()})
        return {"success": True, "message": "Trading started"}

    @app.post("/api/trading/stop")
    async def stop_trading():
        """停止交易"""
        dashboard_state.is_running = False
        await manager.broadcast({"status": dashboard_state.to_dict()})
        return {"success": True, "message": "Trading stopped"}

    @app.get("/api/metrics")
    async def get_metrics():
        """获取性能指标"""
        return {
            "total_equity": 50000.0,
            "daily_return": 0.0,
            "daily_pnl": 0.0,
            "sharpe_ratio": 0.0,
            "max_drawdown": 0.0,
            "fill_rate": 0.0,
            "avg_slippage": 0.0,
            "daily_volume": 0.0,
            "total_trades": 0
        }

    @app.get("/api/positions")
    async def get_positions():
        """获取当前持仓"""
        return []

    @app.get("/api/trades")
    async def get_trades(limit: int = 100):
        """获取交易记录"""
        return dashboard_state.trades_history[:limit]

    @app.get("/api/alerts")
    async def get_alerts(limit: int = 50):
        """获取告警列表"""
        return dashboard_state.alerts[:limit]

    @app.get("/api/reports/generate")
    async def generate_report(format: str = "pdf"):
        """生成报告"""
        try:
            from reports.report_generator import (
                ReportData, ReportConfig,
                PDFReportGenerator, ExcelReportGenerator
            )

            # 准备报告数据
            data = ReportData(
                symbols=dashboard_state.symbols,
                initial_equity=50000.0,
                final_equity=50000.0,
                total_return=0.0,
                sharpe_ratio=0.0,
                max_drawdown=0.0,
                fill_rate=0.0,
                avg_slippage=0.0,
                trades=dashboard_state.trades_history
            )

            config = ReportConfig(output_dir="./reports/output")

            if format.lower() == "pdf":
                generator = PDFReportGenerator(config)
            elif format.lower() in ["excel", "xlsx"]:
                generator = ExcelReportGenerator(config)
            else:
                return JSONResponse(
                    status_code=400,
                    content={"error": f"Unsupported format: {format}"}
                )

            filepath = generator.generate(data)
            return FileResponse(
                filepath,
                filename=Path(filepath).name,
                media_type="application/octet-stream"
            )

        except Exception as e:
            logger.error(f"Report generation failed: {e}")
            return JSONResponse(
                status_code=500,
                content={"error": str(e)}
            )

    @app.get("/api/health")
    async def get_health():
        """获取系统健康状态"""
        try:
            from monitoring.system_dashboard import get_dashboard
            return get_dashboard().get_system_health()
        except Exception as e:
            return {
                "overall_status": "unknown",
                "health_score": 0,
                "error": str(e)
            }

    @app.get("/api/performance")
    async def get_performance():
        """获取性能监控数据"""
        try:
            from monitoring.performance_monitor import get_performance_monitor
            return get_performance_monitor().get_summary()
        except Exception as e:
            return {"error": str(e)}

    @app.get("/api/errors")
    async def get_errors(limit: int = 50):
        """获取错误日志"""
        try:
            from monitoring.error_tracker import get_error_tracker
            errors = get_error_tracker().get_errors(limit=limit)
            return [e.to_dict() for e in errors]
        except Exception as e:
            return {"error": str(e)}

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        """WebSocket 实时推送"""
        await manager.connect(websocket)
        try:
            while True:
                # 接收客户端消息
                data = await websocket.receive_text()
                # 广播状态更新
                await manager.broadcast({
                    "status": dashboard_state.to_dict(),
                    "timestamp": datetime.now().isoformat()
                })
        except WebSocketDisconnect:
            manager.disconnect(websocket)


def run_dashboard(host: str = "0.0.0.0", port: int = 8888):
    """运行仪表盘服务器"""
    if not FASTAPI_AVAILABLE:
        logger.error("FastAPI not installed. Run: pip install fastapi uvicorn")
        return

    logger.info(f"Starting dashboard at http://{host}:{port}")
    uvicorn.run(app, host=host, port=port)


async def push_update(data: Dict[str, Any]):
    """推送更新到所有 WebSocket 客户端"""
    await manager.broadcast(data)


if __name__ == "__main__":
    run_dashboard()
