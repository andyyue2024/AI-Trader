# -*- coding: utf-8 -*-
"""
盘后统计分析模块
自动生成每日收盘后的交易分析报告
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
import math

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class DailyStats:
    """每日统计"""
    date: date
    starting_equity: float = 0.0
    ending_equity: float = 0.0
    pnl: float = 0.0
    pnl_pct: float = 0.0
    trades_count: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    total_volume: float = 0.0
    max_drawdown: float = 0.0
    sharpe_ratio: float = 0.0
    best_trade: float = 0.0
    worst_trade: float = 0.0
    avg_trade_pnl: float = 0.0
    symbols_traded: List[str] = field(default_factory=list)

    @property
    def win_rate(self) -> float:
        if self.trades_count == 0:
            return 0.0
        return self.winning_trades / self.trades_count

    def to_dict(self) -> Dict:
        return {
            "date": self.date.isoformat(),
            "starting_equity": self.starting_equity,
            "ending_equity": self.ending_equity,
            "pnl": round(self.pnl, 2),
            "pnl_pct": round(self.pnl_pct * 100, 2),
            "trades_count": self.trades_count,
            "win_rate": round(self.win_rate * 100, 2),
            "total_volume": round(self.total_volume, 2),
            "max_drawdown": round(self.max_drawdown * 100, 2),
            "sharpe_ratio": round(self.sharpe_ratio, 2),
            "best_trade": round(self.best_trade, 2),
            "worst_trade": round(self.worst_trade, 2),
            "symbols_traded": self.symbols_traded
        }


@dataclass
class WeeklyStats:
    """每周统计"""
    week_start: date
    week_end: date
    daily_stats: List[DailyStats] = field(default_factory=list)

    @property
    def total_pnl(self) -> float:
        return sum(d.pnl for d in self.daily_stats)

    @property
    def total_trades(self) -> int:
        return sum(d.trades_count for d in self.daily_stats)

    @property
    def avg_daily_pnl(self) -> float:
        if not self.daily_stats:
            return 0.0
        return self.total_pnl / len(self.daily_stats)

    @property
    def best_day(self) -> Optional[DailyStats]:
        if not self.daily_stats:
            return None
        return max(self.daily_stats, key=lambda d: d.pnl)

    @property
    def worst_day(self) -> Optional[DailyStats]:
        if not self.daily_stats:
            return None
        return min(self.daily_stats, key=lambda d: d.pnl)


class PostMarketAnalyzer:
    """盘后分析器"""

    def __init__(self, data_dir: str = "./data/agent_data"):
        self.data_dir = Path(data_dir)
        self.stats_dir = Path("./reports/stats")
        self.stats_dir.mkdir(parents=True, exist_ok=True)

        self.daily_returns: List[float] = []
        self.equity_history: List[Dict] = []

    def analyze_day(
        self,
        trades: List[Dict],
        starting_equity: float,
        ending_equity: float,
        target_date: date = None
    ) -> DailyStats:
        """分析单日交易"""
        target_date = target_date or date.today()

        stats = DailyStats(date=target_date)
        stats.starting_equity = starting_equity
        stats.ending_equity = ending_equity
        stats.pnl = ending_equity - starting_equity
        stats.pnl_pct = stats.pnl / starting_equity if starting_equity > 0 else 0

        if trades:
            stats.trades_count = len(trades)
            pnls = [t.get("pnl", 0) for t in trades]
            stats.winning_trades = len([p for p in pnls if p > 0])
            stats.losing_trades = len([p for p in pnls if p < 0])
            stats.best_trade = max(pnls) if pnls else 0
            stats.worst_trade = min(pnls) if pnls else 0
            stats.avg_trade_pnl = sum(pnls) / len(pnls) if pnls else 0
            stats.total_volume = sum(abs(t.get("quantity", 0) * t.get("price", 0)) for t in trades)
            stats.symbols_traded = list(set(t.get("symbol", "") for t in trades))

        # 计算夏普比率（基于日收益率）
        self.daily_returns.append(stats.pnl_pct)
        if len(self.daily_returns) >= 5:
            avg_ret = sum(self.daily_returns) / len(self.daily_returns)
            std_ret = math.sqrt(sum((r - avg_ret) ** 2 for r in self.daily_returns) / len(self.daily_returns))
            if std_ret > 0:
                stats.sharpe_ratio = (avg_ret * 252) / (std_ret * math.sqrt(252))

        return stats

    def generate_daily_report(self, stats: DailyStats) -> str:
        """生成每日报告"""
        report = f"""
╔══════════════════════════════════════════════════════════════╗
║                    📊 Daily Trading Report                    ║
║                       {stats.date.isoformat()}                         ║
╠══════════════════════════════════════════════════════════════╣
║  Performance Summary                                          ║
║  ─────────────────────────────────────────────────────────   ║
║  Starting Equity:    ${stats.starting_equity:>12,.2f}                  ║
║  Ending Equity:      ${stats.ending_equity:>12,.2f}                  ║
║  Daily P&L:          ${stats.pnl:>+12,.2f} ({stats.pnl_pct*100:>+.2f}%)           ║
╠══════════════════════════════════════════════════════════════╣
║  Trading Activity                                             ║
║  ─────────────────────────────────────────────────────────   ║
║  Total Trades:       {stats.trades_count:>12}                          ║
║  Winning Trades:     {stats.winning_trades:>12}                          ║
║  Losing Trades:      {stats.losing_trades:>12}                          ║
║  Win Rate:           {stats.win_rate*100:>11.1f}%                         ║
║  Total Volume:       ${stats.total_volume:>12,.2f}                  ║
╠══════════════════════════════════════════════════════════════╣
║  Trade Statistics                                             ║
║  ─────────────────────────────────────────────────────────   ║
║  Best Trade:         ${stats.best_trade:>+12,.2f}                  ║
║  Worst Trade:        ${stats.worst_trade:>+12,.2f}                  ║
║  Average Trade:      ${stats.avg_trade_pnl:>+12,.2f}                  ║
╠══════════════════════════════════════════════════════════════╣
║  Risk Metrics                                                 ║
║  ─────────────────────────────────────────────────────────   ║
║  Sharpe Ratio:       {stats.sharpe_ratio:>12.2f}                         ║
║  Max Drawdown:       {stats.max_drawdown*100:>11.2f}%                         ║
╠══════════════════════════════════════════════════════════════╣
║  Symbols Traded: {', '.join(stats.symbols_traded[:5]):<40}  ║
╚══════════════════════════════════════════════════════════════╝
"""
        return report

    def save_stats(self, stats: DailyStats):
        """保存统计数据"""
        filepath = self.stats_dir / f"daily_stats_{stats.date.isoformat()}.json"
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(stats.to_dict(), f, indent=2, ensure_ascii=False)
        logger.info(f"Stats saved to {filepath}")

    def load_stats(self, target_date: date) -> Optional[DailyStats]:
        """加载统计数据"""
        filepath = self.stats_dir / f"daily_stats_{target_date.isoformat()}.json"
        if not filepath.exists():
            return None

        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        stats = DailyStats(date=target_date)
        for key, value in data.items():
            if key != "date" and hasattr(stats, key):
                setattr(stats, key, value)

        return stats

    def get_weekly_summary(self, week_start: date = None) -> WeeklyStats:
        """获取周统计"""
        if week_start is None:
            week_start = date.today() - timedelta(days=date.today().weekday())

        week_end = week_start + timedelta(days=4)  # 周五

        daily_stats = []
        current = week_start
        while current <= week_end:
            stats = self.load_stats(current)
            if stats:
                daily_stats.append(stats)
            current += timedelta(days=1)

        return WeeklyStats(
            week_start=week_start,
            week_end=week_end,
            daily_stats=daily_stats
        )

    def generate_weekly_report(self, weekly: WeeklyStats) -> str:
        """生成周报告"""
        report = f"""
╔══════════════════════════════════════════════════════════════╗
║                    📈 Weekly Trading Report                   ║
║              {weekly.week_start.isoformat()} to {weekly.week_end.isoformat()}              ║
╠══════════════════════════════════════════════════════════════╣
║  Weekly Performance                                           ║
║  ─────────────────────────────────────────────────────────   ║
║  Total P&L:          ${weekly.total_pnl:>+12,.2f}                  ║
║  Trading Days:       {len(weekly.daily_stats):>12}                          ║
║  Total Trades:       {weekly.total_trades:>12}                          ║
║  Avg Daily P&L:      ${weekly.avg_daily_pnl:>+12,.2f}                  ║
╠══════════════════════════════════════════════════════════════╣
║  Daily Breakdown                                              ║
║  ─────────────────────────────────────────────────────────   ║
"""
        for ds in weekly.daily_stats:
            status = "🟢" if ds.pnl >= 0 else "🔴"
            report += f"║  {status} {ds.date.isoformat()}:  ${ds.pnl:>+10,.2f}  ({ds.trades_count:>3} trades)      ║\n"

        if weekly.best_day:
            report += f"""╠══════════════════════════════════════════════════════════════╣
║  Best Day:   {weekly.best_day.date.isoformat()} (${weekly.best_day.pnl:>+,.2f})               ║
║  Worst Day:  {weekly.worst_day.date.isoformat()} (${weekly.worst_day.pnl:>+,.2f})               ║
"""
        report += "╚══════════════════════════════════════════════════════════════╝\n"

        return report

    def run_post_market_analysis(
        self,
        trades: List[Dict],
        starting_equity: float,
        ending_equity: float
    ) -> DailyStats:
        """运行盘后分析"""
        logger.info("Running post-market analysis...")

        # 分析今日交易
        stats = self.analyze_day(trades, starting_equity, ending_equity)

        # 生成报告
        report = self.generate_daily_report(stats)
        print(report)

        # 保存统计
        self.save_stats(stats)

        # 如果是周五，生成周报
        if stats.date.weekday() == 4:  # Friday
            weekly = self.get_weekly_summary()
            weekly_report = self.generate_weekly_report(weekly)
            print(weekly_report)

        return stats


if __name__ == "__main__":
    # 示例使用
    analyzer = PostMarketAnalyzer()

    # 模拟交易数据
    sample_trades = [
        {"symbol": "TQQQ", "side": "long", "quantity": 100, "price": 50.0, "pnl": 150.0},
        {"symbol": "QQQ", "side": "short", "quantity": 50, "price": 400.0, "pnl": -80.0},
        {"symbol": "TQQQ", "side": "flat", "quantity": 100, "price": 52.0, "pnl": 200.0},
    ]

    stats = analyzer.run_post_market_analysis(
        trades=sample_trades,
        starting_equity=50000.0,
        ending_equity=50270.0
    )
