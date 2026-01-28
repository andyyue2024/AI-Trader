# -*- coding: utf-8 -*-
"""
AI-Trader Web UI - 优化版
基于 FastAPI 的现代化 Web 仪表盘
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

try:
    from fastapi import FastAPI, WebSocket, WebSocketDisconnect
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
    import uvicorn
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if FASTAPI_AVAILABLE:
    app = FastAPI(title="AI-Trader Dashboard", version="2.0.0")
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
else:
    app = None


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for conn in self.active_connections:
            try:
                await conn.send_json(message)
            except:
                pass


manager = ConnectionManager()


class DashboardState:
    def __init__(self):
        self.is_running = False
        self.symbols = ["TQQQ", "QQQ"]
        self.last_update = None
        self.trades_history = []
        self.alerts = []
        self.positions = []
        self.metrics = {"total_equity": 50000.0, "daily_pnl": 0.0, "daily_return": 0.0, "sharpe_ratio": 0.0, "max_drawdown": 0.0, "fill_rate": 0.0, "avg_slippage": 0.0, "daily_volume": 0.0, "total_trades": 0, "win_rate": 0.0, "order_latency": 0.0, "loop_time": 0.0}

    def to_dict(self):
        return {"is_running": self.is_running, "symbols": self.symbols, "last_update": self.last_update.isoformat() if self.last_update else None}


dashboard_state = DashboardState()

DASHBOARD_HTML = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AI-Trader Dashboard</title>
<script src="https://cdn.tailwindcss.com"></script>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
:root{--bg:#0f172a;--card:#1e293b;--text:#f8fafc;--muted:#94a3b8;--green:#22c55e;--red:#ef4444;--blue:#3b82f6}
*{font-family:'Inter',system-ui,sans-serif}body{background:var(--bg);color:var(--text);margin:0}
.card{background:var(--card);border-radius:12px;border:1px solid rgba(148,163,184,0.1)}
.pulse{animation:pulse 2s infinite}@keyframes pulse{0%,100%{opacity:1}50%{opacity:0.5}}
.btn{padding:8px 16px;border-radius:8px;font-weight:500;transition:all 0.2s}
.btn-green{background:linear-gradient(135deg,#22c55e,#16a34a)}.btn-red{background:linear-gradient(135deg,#ef4444,#dc2626)}
.btn-blue{background:linear-gradient(135deg,#3b82f6,#2563eb)}
.progress{height:6px;background:rgba(148,163,184,0.2);border-radius:3px;overflow:hidden}
.progress-bar{height:100%;transition:width 0.5s}
.target-ok{color:var(--green)}.target-miss{color:var(--red)}
</style>
</head>
<body>
<nav class="card mx-4 mt-4 px-6 py-4 flex justify-between items-center">
<div class="flex items-center gap-3">
<span class="text-2xl">🚀</span>
<div><h1 class="text-xl font-bold">AI-Trader</h1><p class="text-xs text-gray-400">High Frequency Trading</p></div>
</div>
<div class="flex items-center gap-4">
<div class="flex items-center gap-2"><div id="status-dot" class="w-2 h-2 rounded-full bg-red-500 pulse"></div><span id="status-text" class="text-sm">Offline</span></div>
<span id="clock" class="text-sm text-gray-400">--:--:--</span>
<span id="session" class="text-xs px-2 py-1 rounded bg-gray-700">--</span>
</div>
</nav>

<main class="p-4 space-y-4">
<div class="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
<div class="card p-4"><div class="text-xs text-gray-400">Equity</div><div class="text-2xl font-bold" id="equity">$50,000</div><div class="text-xs" id="equity-chg"><span class="text-green-400">+$0</span></div></div>
<div class="card p-4"><div class="text-xs text-gray-400">Today P&L</div><div class="text-2xl font-bold" id="pnl">$0</div><div class="text-xs text-gray-500" id="trades">0 trades</div></div>
<div class="card p-4"><div class="text-xs text-gray-400">Sharpe</div><div class="text-2xl font-bold" id="sharpe">0.00</div><div class="text-xs"><span id="sharpe-s" class="target-miss">Target: ≥2</span></div></div>
<div class="card p-4"><div class="text-xs text-gray-400">Drawdown</div><div class="text-2xl font-bold" id="dd">0%</div><div class="text-xs"><span id="dd-s" class="target-ok">Target: ≤15%</span></div></div>
<div class="card p-4"><div class="text-xs text-gray-400">Fill Rate</div><div class="text-2xl font-bold" id="fill">0%</div><div class="progress mt-2"><div id="fill-bar" class="progress-bar bg-blue-500" style="width:0"></div></div></div>
<div class="card p-4"><div class="text-xs text-gray-400">Volume</div><div class="text-2xl font-bold" id="vol">$0</div><div class="text-xs"><span id="vol-s" class="target-miss">Target: ≥$50k</span></div></div>
</div>

<div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
<div class="lg:col-span-2 space-y-4">
<div class="card p-4"><div class="flex justify-between mb-3"><h3 class="font-semibold">Equity Curve</h3><div class="flex gap-1 text-xs"><button class="px-2 py-1 rounded bg-gray-700">1H</button><button class="px-2 py-1 rounded bg-blue-600">1D</button><button class="px-2 py-1 rounded bg-gray-700">1W</button></div></div><div style="height:220px"><canvas id="chart-equity"></canvas></div></div>
<div class="grid grid-cols-2 gap-4">
<div class="card p-4"><h3 class="font-semibold mb-3">P&L Distribution</h3><div style="height:160px"><canvas id="chart-pnl"></canvas></div></div>
<div class="card p-4"><h3 class="font-semibold mb-3">Latency</h3><div style="height:160px"><canvas id="chart-lat"></canvas></div></div>
</div>
</div>

<div class="space-y-4">
<div class="card p-4"><div class="flex justify-between mb-3"><h3 class="font-semibold">Positions</h3><span class="text-xs text-gray-400" id="pos-cnt">0</span></div><div id="positions" class="space-y-2 max-h-40 overflow-auto"><div class="text-center text-gray-500 py-6 text-sm">No positions</div></div></div>
<div class="card p-4"><div class="flex justify-between mb-3"><h3 class="font-semibold">Trades</h3><span class="text-xs text-blue-400 cursor-pointer">View All</span></div><div id="trade-list" class="space-y-2 max-h-52 overflow-auto"><div class="text-center text-gray-500 py-6 text-sm">No trades</div></div></div>
<div class="card p-4"><div class="flex justify-between mb-3"><h3 class="font-semibold">Alerts</h3><span class="text-xs px-2 py-0.5 rounded-full bg-red-500/20 text-red-400" id="alert-cnt">0</span></div><div id="alerts" class="space-y-2 max-h-32 overflow-auto"><div class="text-center text-gray-500 py-4 text-sm">No alerts</div></div></div>
</div>
</div>

<div class="card p-4 flex flex-wrap justify-between items-center gap-4">
<div class="flex items-center gap-4">
<div class="flex items-center gap-2"><span class="text-sm text-gray-400">Symbols:</span><input id="sym" value="TQQQ,QQQ" class="bg-gray-800 border border-gray-700 rounded px-3 py-1 text-sm w-32"></div>
<div class="flex items-center gap-2"><span class="text-sm text-gray-400">Mode:</span><select id="mode" class="bg-gray-800 border border-gray-700 rounded px-3 py-1 text-sm"><option value="dry">Dry Run</option><option value="live">Live</option></select></div>
</div>
<div class="flex gap-2">
<button onclick="start()" class="btn btn-green">▶ Start</button>
<button onclick="stop()" class="btn btn-red">⏹ Stop</button>
<button onclick="report()" class="btn btn-blue">📊 Report</button>
</div>
</div>

<div class="card p-4"><h3 class="font-semibold mb-3">Performance Targets</h3>
<div class="grid grid-cols-2 md:grid-cols-4 gap-3">
<div class="bg-gray-800/50 rounded-lg p-3"><div class="flex justify-between mb-1"><span class="text-xs text-gray-400">Order Latency</span><span id="lat-s" class="text-xs px-2 py-0.5 rounded-full bg-green-500/20 text-green-400">OK</span></div><div class="text-lg font-bold" id="lat">0.0ms</div><div class="text-xs text-gray-500">Target: ≤1.4ms</div></div>
<div class="bg-gray-800/50 rounded-lg p-3"><div class="flex justify-between mb-1"><span class="text-xs text-gray-400">Loop Time</span><span id="loop-s" class="text-xs px-2 py-0.5 rounded-full bg-green-500/20 text-green-400">OK</span></div><div class="text-lg font-bold" id="loop">0ms</div><div class="text-xs text-gray-500">Target: ≤1000ms</div></div>
<div class="bg-gray-800/50 rounded-lg p-3"><div class="flex justify-between mb-1"><span class="text-xs text-gray-400">Slippage</span><span id="slip-s" class="text-xs px-2 py-0.5 rounded-full bg-green-500/20 text-green-400">OK</span></div><div class="text-lg font-bold" id="slip">0.00%</div><div class="text-xs text-gray-500">Target: ≤0.2%</div></div>
<div class="bg-gray-800/50 rounded-lg p-3"><div class="flex justify-between mb-1"><span class="text-xs text-gray-400">Win Rate</span><span id="wr-s" class="text-xs px-2 py-0.5 rounded-full bg-yellow-500/20 text-yellow-400">--</span></div><div class="text-lg font-bold" id="wr">0%</div><div class="text-xs text-gray-500">Target: ≥50%</div></div>
</div>
</div>
</main>

<script>
let ws,eqChart,pnlChart,latChart;
const $=id=>document.getElementById(id);

function init(){
initCharts();initWS();setInterval(()=>$('clock').textContent=new Date().toLocaleTimeString(),1000);
fetch('/api/status').then(r=>r.json()).then(update).catch(()=>{});
}

function initWS(){
ws=new WebSocket(`ws://${location.host}/ws`);
ws.onopen=()=>{$('status-dot').className='w-2 h-2 rounded-full bg-green-500 pulse';$('status-text').textContent='Online'};
ws.onclose=()=>{$('status-dot').className='w-2 h-2 rounded-full bg-red-500 pulse';$('status-text').textContent='Offline';setTimeout(initWS,3000)};
ws.onmessage=e=>update(JSON.parse(e.data));
}

function initCharts(){
const opts={responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false}},scales:{x:{grid:{color:'rgba(148,163,184,0.1)'},ticks:{color:'#94a3b8'}},y:{grid:{color:'rgba(148,163,184,0.1)'},ticks:{color:'#94a3b8'}}}};
eqChart=new Chart($('chart-equity'),{type:'line',data:{labels:[],datasets:[{data:[],borderColor:'#3b82f6',backgroundColor:'rgba(59,130,246,0.1)',fill:true,tension:0.4,pointRadius:0}]},options:opts});
pnlChart=new Chart($('chart-pnl'),{type:'bar',data:{labels:[],datasets:[{data:[],backgroundColor:[]}]},options:opts});
latChart=new Chart($('chart-lat'),{type:'line',data:{labels:[],datasets:[{label:'Loop',data:[],borderColor:'#3b82f6',tension:0.4,pointRadius:0},{label:'Order',data:[],borderColor:'#22c55e',tension:0.4,pointRadius:0}]},options:{...opts,plugins:{legend:{display:true,labels:{color:'#94a3b8'}}}}});
}

function update(d){
if(d.metrics)updateMetrics(d.metrics);
if(d.positions)updatePositions(d.positions);
if(d.trades)updateTrades(d.trades);
if(d.alerts)updateAlerts(d.alerts);
if(d.session)$('session').textContent={'pre_market':'🌅Pre','regular':'📈Regular','after_hours':'🌙After','closed':'🔒Closed'}[d.session.current_session]||'--';
}

function updateMetrics(m){
const eq=m.total_equity||50000,pnl=m.daily_pnl||0,ret=m.daily_return||0;
$('equity').textContent='$'+eq.toLocaleString(undefined,{minimumFractionDigits:2});
$('equity-chg').innerHTML=`<span class="${pnl>=0?'text-green-400':'text-red-400'}">${pnl>=0?'+':''}$${pnl.toFixed(2)}</span>`;
$('pnl').textContent=(pnl>=0?'+':'')+' $'+pnl.toFixed(2);$('pnl').className='text-2xl font-bold '+(pnl>=0?'text-green-400':'text-red-400');
$('trades').textContent=(m.total_trades||0)+' trades';
$('sharpe').textContent=(m.sharpe_ratio||0).toFixed(2);$('sharpe-s').className=(m.sharpe_ratio||0)>=2?'target-ok':'target-miss';
const dd=(m.max_drawdown||0)*100;$('dd').textContent=dd.toFixed(2)+'%';$('dd-s').className=dd<=15?'target-ok':'target-miss';
const fr=(m.fill_rate||0)*100;$('fill').textContent=fr.toFixed(1)+'%';$('fill-bar').style.width=fr+'%';
$('vol').textContent='$'+(m.daily_volume||0).toLocaleString();$('vol-s').className=(m.daily_volume||0)>=50000?'target-ok':'target-miss';
$('lat').textContent=(m.order_latency||0).toFixed(2)+'ms';$('loop').textContent=(m.loop_time||0).toFixed(0)+'ms';
$('slip').textContent=((m.avg_slippage||0)*100).toFixed(4)+'%';$('wr').textContent=((m.win_rate||0)*100).toFixed(1)+'%';
setStatus('lat-s',(m.order_latency||0)<=1.4);setStatus('loop-s',(m.loop_time||0)<=1000);
setStatus('slip-s',(m.avg_slippage||0)<=0.002);setStatus('wr-s',(m.win_rate||0)>=0.5);
}

function setStatus(id,ok){$(id).className='text-xs px-2 py-0.5 rounded-full '+(ok?'bg-green-500/20 text-green-400':'bg-red-500/20 text-red-400');$(id).textContent=ok?'OK':'MISS'}

function updatePositions(p){
$('pos-cnt').textContent=p.length+' positions';
$('positions').innerHTML=p.length?p.map(x=>`<div class="flex justify-between items-center p-2 bg-gray-800/50 rounded"><div><span class="font-medium">${x.symbol}</span><span class="ml-2 text-xs ${x.side==='long'?'text-green-400':'text-red-400'}">${x.side.toUpperCase()}</span></div><div class="text-right"><div class="text-sm">${x.quantity}@$${(x.avg_cost||0).toFixed(2)}</div><div class="text-xs ${(x.pnl||0)>=0?'text-green-400':'text-red-400'}">${(x.pnl||0)>=0?'+':''}$${(x.pnl||0).toFixed(2)}</div></div></div>`).join(''):'<div class="text-center text-gray-500 py-6 text-sm">No positions</div>';
}

function updateTrades(t){
$('trade-list').innerHTML=t.length?t.slice(0,10).map(x=>`<div class="flex justify-between items-center p-2 rounded hover:bg-blue-500/10"><div class="flex items-center gap-2"><span class="w-2 h-2 rounded-full ${x.side==='long'?'bg-green-400':'bg-red-400'}"></span><span class="font-medium text-sm">${x.symbol}</span></div><div class="text-xs text-gray-400">${x.quantity}@$${(x.price||0).toFixed(2)}</div><div class="text-xs ${(x.pnl||0)>=0?'text-green-400':'text-red-400'}">${(x.pnl||0)>=0?'+':''}$${(x.pnl||0).toFixed(2)}</div></div>`).join(''):'<div class="text-center text-gray-500 py-6 text-sm">No trades</div>';
}

function updateAlerts(a){
$('alert-cnt').textContent=a.length;
const c={critical:'border-red-500 bg-red-500/10',error:'border-red-400 bg-red-400/10',warning:'border-yellow-500 bg-yellow-500/10',info:'border-blue-500 bg-blue-500/10'};
$('alerts').innerHTML=a.length?a.slice(0,5).map(x=>`<div class="p-2 rounded border-l-2 ${c[x.level]||c.info}"><div class="text-sm font-medium">${x.title}</div><div class="text-xs text-gray-400">${x.message}</div></div>`).join(''):'<div class="text-center text-gray-500 py-4 text-sm">No alerts</div>';
}

async function start(){
const r=await fetch('/api/trading/start',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({symbols:$('sym').value.split(','),dry_run:$('mode').value==='dry'})});
const d=await r.json();notify(d.success?'Trading started':'Failed','success');
}
async function stop(){await fetch('/api/trading/stop',{method:'POST'});notify('Trading stopped','info')}
function report(){window.open('/api/reports/generate?format=pdf','_blank')}
function notify(msg,type){const d=document.createElement('div');d.className='fixed top-4 right-4 px-4 py-2 rounded-lg shadow-lg z-50 '+(type==='success'?'bg-green-500':'bg-blue-500');d.textContent=msg;document.body.appendChild(d);setTimeout(()=>d.remove(),3000)}

document.addEventListener('DOMContentLoaded',init);
</script>
</body>
</html>'''


if FASTAPI_AVAILABLE:
    @app.get("/", response_class=HTMLResponse)
    async def root():
        return DASHBOARD_HTML

    @app.get("/api/status")
    async def get_status():
        return {"status": dashboard_state.to_dict(), "metrics": dashboard_state.metrics, "positions": dashboard_state.positions, "trades": dashboard_state.trades_history[-20:], "alerts": dashboard_state.alerts[-10:], "session": {"current_session": "regular", "can_trade": True}}

    @app.post("/api/trading/start")
    async def start_trading(data: dict = None):
        dashboard_state.is_running = True
        if data:
            dashboard_state.symbols = data.get("symbols", ["TQQQ", "QQQ"])
        await manager.broadcast({"status": dashboard_state.to_dict()})
        return {"success": True}

    @app.post("/api/trading/stop")
    async def stop_trading():
        dashboard_state.is_running = False
        await manager.broadcast({"status": dashboard_state.to_dict()})
        return {"success": True}

    @app.get("/api/metrics")
    async def get_metrics():
        return dashboard_state.metrics

    @app.get("/api/positions")
    async def get_positions():
        return dashboard_state.positions

    @app.get("/api/trades")
    async def get_trades(limit: int = 100):
        return dashboard_state.trades_history[-limit:]

    @app.get("/api/alerts")
    async def get_alerts(limit: int = 50):
        return dashboard_state.alerts[-limit:]

    @app.get("/api/reports/generate")
    async def generate_report(format: str = "pdf"):
        try:
            from reports.report_generator import ReportData, ReportConfig, PDFReportGenerator, ExcelReportGenerator
            data = ReportData(symbols=dashboard_state.symbols, initial_equity=50000.0)
            config = ReportConfig(output_dir="./reports/output")
            gen = PDFReportGenerator(config) if format == "pdf" else ExcelReportGenerator(config)
            filepath = gen.generate(data)
            return FileResponse(filepath, filename=Path(filepath).name)
        except Exception as e:
            return JSONResponse(status_code=500, content={"error": str(e)})

    @app.get("/api/health")
    async def get_health():
        return {"status": "healthy", "timestamp": datetime.now().isoformat()}

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        await manager.connect(websocket)
        try:
            while True:
                await websocket.receive_text()
                await manager.broadcast({"status": dashboard_state.to_dict(), "metrics": dashboard_state.metrics, "timestamp": datetime.now().isoformat()})
        except WebSocketDisconnect:
            manager.disconnect(websocket)


def run_dashboard(host: str = "0.0.0.0", port: int = 8888):
    if not FASTAPI_AVAILABLE:
        logger.error("FastAPI not installed. Run: pip install fastapi uvicorn")
        return
    logger.info(f"Starting dashboard at http://{host}:{port}")
    uvicorn.run(app, host=host, port=port)


async def push_update(data: Dict[str, Any]):
    await manager.broadcast(data)


if __name__ == "__main__":
    run_dashboard()
