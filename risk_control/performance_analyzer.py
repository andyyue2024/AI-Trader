# -*- coding: utf-8 -*-
"""
交易绩效分析器
计算夏普比率、最大回撤、成交率等关键指标
目标：夏普 ≥ 2，最大回撤 ≤ 15%，成交率 ≥ 95%
"""

import json
import logging
import math
import os
from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
import threading

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class TradeRecord:
    """交易记录"""
    trade_id: str
    symbol: str
    side: str  # long/short/flat
    quantity: int
    entry_price: float
    exit_price: Optional[float] = None
    entry_time: datetime = field(default_factory=datetime.now)
    exit_time: Optional[datetime] = None
    pnl: float = 0.0
    commission: float = 0.0
    slippage: float = 0.0
    status: str = "open"  # open/closed

    @property
    def is_closed(self) -> bool:
        return self.status == "closed"

    @property
    def gross_pnl(self) -> float:
        """毛利润"""
        if not self.is_closed or self.exit_price is None:
            return 0.0
        if self.side == "long":
            return (self.exit_price - self.entry_price) * self.quantity
        elif self.side == "short":
            return (self.entry_price - self.exit_price) * self.quantity
        return 0.0

    @property
    def net_pnl(self) -> float:
        """净利润"""
        return self.gross_pnl - self.commission

    @property
    def return_pct(self) -> float:
        """收益率"""
        if self.entry_price > 0:
            return self.gross_pnl / (self.entry_price * self.quantity)
        return 0.0

    @property
    def holding_time(self) -> Optional[timedelta]:
        """持仓时间"""
        if self.exit_time:
            return self.exit_time - self.entry_time
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trade_id": self.trade_id,
            "symbol": self.symbol,
            "side": self.side,
            "quantity": self.quantity,
            "entry_price": self.entry_price,
            "exit_price": self.exit_price,
            "entry_time": self.entry_time.isoformat(),
            "exit_time": self.exit_time.isoformat() if self.exit_time else None,
            "pnl": round(self.net_pnl, 2),
            "return_pct": round(self.return_pct, 4),
            "commission": self.commission,
            "slippage": round(self.slippage, 6),
            "status": self.status
        }


@dataclass
class DailyStats:
    """每日统计"""
    date: date
    starting_equity: float
    ending_equity: float
    high_watermark: float
    low_watermark: float
    total_pnl: float = 0.0
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0
    trade_count: int = 0
    win_count: int = 0
    loss_count: int = 0
    total_volume: float = 0.0  # 成交额
    total_commission: float = 0.0

    @property
    def daily_return(self) -> float:
        """日收益率"""
        if self.starting_equity > 0:
            return (self.ending_equity - self.starting_equity) / self.starting_equity
        return 0.0

    @property
    def drawdown(self) -> float:
        """日内回撤"""
        if self.high_watermark > 0:
            return (self.high_watermark - self.low_watermark) / self.high_watermark
        return 0.0

    @property
    def win_rate(self) -> float:
        """胜率"""
        if self.trade_count > 0:
            return self.win_count / self.trade_count
        return 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "date": self.date.isoformat(),
            "starting_equity": self.starting_equity,
            "ending_equity": self.ending_equity,
            "daily_return": round(self.daily_return, 4),
            "drawdown": round(self.drawdown, 4),
            "total_pnl": round(self.total_pnl, 2),
            "trade_count": self.trade_count,
            "win_rate": round(self.win_rate, 4),
            "total_volume": round(self.total_volume, 2),
            "total_commission": round(self.total_commission, 2)
        }


@dataclass
class PerformanceMetrics:
    """绩效指标"""
    # 收益指标
    total_return: float = 0.0
    annualized_return: float = 0.0

    # 风险指标
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    max_drawdown: float = 0.0
    max_drawdown_duration: int = 0  # 天数
    volatility: float = 0.0

    # 交易指标
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    avg_trade: float = 0.0

    # 成交指标
    total_volume: float = 0.0  # 总成交额
    avg_daily_volume: float = 0.0  # 日均成交额
    fill_rate: float = 0.0  # 成交率
    avg_slippage: float = 0.0

    # 时间统计
    trading_days: int = 0
    avg_holding_time: float = 0.0  # 小时

    def meets_targets(self,
                      target_sharpe: float = 2.0,
                      target_max_dd: float = 0.15,
                      target_daily_volume: float = 50000,
                      target_fill_rate: float = 0.95) -> Dict[str, bool]:
        """检查是否达标"""
        return {
            "sharpe_ratio": self.sharpe_ratio >= target_sharpe,
            "max_drawdown": self.max_drawdown <= target_max_dd,
            "daily_volume": self.avg_daily_volume >= target_daily_volume,
            "fill_rate": self.fill_rate >= target_fill_rate
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "returns": {
                "total_return": round(self.total_return, 4),
                "annualized_return": round(self.annualized_return, 4)
            },
            "risk": {
                "sharpe_ratio": round(self.sharpe_ratio, 2),
                "sortino_ratio": round(self.sortino_ratio, 2),
                "max_drawdown": round(self.max_drawdown, 4),
                "max_drawdown_duration_days": self.max_drawdown_duration,
                "volatility": round(self.volatility, 4)
            },
            "trading": {
                "total_trades": self.total_trades,
                "winning_trades": self.winning_trades,
                "losing_trades": self.losing_trades,
                "win_rate": round(self.win_rate, 4),
                "profit_factor": round(self.profit_factor, 2),
                "avg_win": round(self.avg_win, 2),
                "avg_loss": round(self.avg_loss, 2),
                "avg_trade": round(self.avg_trade, 2)
            },
            "execution": {
                "total_volume": round(self.total_volume, 2),
                "avg_daily_volume": round(self.avg_daily_volume, 2),
                "fill_rate": round(self.fill_rate, 4),
                "avg_slippage": round(self.avg_slippage, 6)
            },
            "time": {
                "trading_days": self.trading_days,
                "avg_holding_time_hours": round(self.avg_holding_time, 2)
            },
            "targets_met": self.meets_targets()
        }


class PerformanceAnalyzer:
    """
    绩效分析器
    计算和跟踪交易绩效
    """

    RISK_FREE_RATE = 0.05  # 年化无风险利率 5%
    TRADING_DAYS_PER_YEAR = 252

    def __init__(self, initial_equity: float = 50000.0):
        self.initial_equity = initial_equity
        self.current_equity = initial_equity
        self._trades: List[TradeRecord] = []
        self._daily_stats: List[DailyStats] = []
        self._daily_returns: List[float] = []
        self._equity_curve: List[Tuple[datetime, float]] = []
        self._lock = threading.Lock()

        # 订单统计
        self._orders_submitted = 0
        self._orders_filled = 0
        self._orders_rejected = 0
        self._total_slippage = 0.0

        # 当日统计
        self._today_stats: Optional[DailyStats] = None
        self._high_watermark = initial_equity

    def record_trade(self, trade: TradeRecord):
        """记录交易"""
        with self._lock:
            self._trades.append(trade)

            if trade.is_closed:
                # 更新权益
                self.current_equity += trade.net_pnl
                self._equity_curve.append((datetime.now(), self.current_equity))

                # 更新高水位
                if self.current_equity > self._high_watermark:
                    self._high_watermark = self.current_equity

                # 更新当日统计
                self._update_daily_stats(trade)

    def record_order(self, submitted: bool = True, filled: bool = False,
                    rejected: bool = False, slippage: float = 0.0):
        """记录订单"""
        with self._lock:
            if submitted:
                self._orders_submitted += 1
            if filled:
                self._orders_filled += 1
            if rejected:
                self._orders_rejected += 1
            self._total_slippage += abs(slippage)

    def _update_daily_stats(self, trade: TradeRecord):
        """更新当日统计"""
        today = date.today()

        if self._today_stats is None or self._today_stats.date != today:
            # 保存前一天统计
            if self._today_stats:
                self._daily_stats.append(self._today_stats)
                self._daily_returns.append(self._today_stats.daily_return)

            # 创建新的当日统计
            self._today_stats = DailyStats(
                date=today,
                starting_equity=self.current_equity - trade.net_pnl,
                ending_equity=self.current_equity,
                high_watermark=self.current_equity,
                low_watermark=self.current_equity
            )

        # 更新统计
        self._today_stats.ending_equity = self.current_equity
        self._today_stats.high_watermark = max(self._today_stats.high_watermark, self.current_equity)
        self._today_stats.low_watermark = min(self._today_stats.low_watermark, self.current_equity)
        self._today_stats.total_pnl += trade.net_pnl
        self._today_stats.realized_pnl += trade.net_pnl
        self._today_stats.trade_count += 1
        self._today_stats.total_volume += trade.entry_price * trade.quantity
        self._today_stats.total_commission += trade.commission

        if trade.net_pnl > 0:
            self._today_stats.win_count += 1
        elif trade.net_pnl < 0:
            self._today_stats.loss_count += 1

    def calculate_sharpe_ratio(self, returns: List[float] = None) -> float:
        """
        计算夏普比率
        Sharpe = (Rp - Rf) / σp
        """
        if returns is None:
            returns = self._daily_returns

        if len(returns) < 2:
            return 0.0

        avg_return = sum(returns) / len(returns)
        daily_rf = self.RISK_FREE_RATE / self.TRADING_DAYS_PER_YEAR
        excess_return = avg_return - daily_rf

        # 计算标准差
        variance = sum((r - avg_return) ** 2 for r in returns) / len(returns)
        std_dev = math.sqrt(variance)

        if std_dev == 0:
            return 0.0

        # 年化夏普
        sharpe = (excess_return / std_dev) * math.sqrt(self.TRADING_DAYS_PER_YEAR)
        return sharpe

    def calculate_sortino_ratio(self, returns: List[float] = None) -> float:
        """
        计算索提诺比率
        Sortino = (Rp - Rf) / σd (只考虑下行风险)
        """
        if returns is None:
            returns = self._daily_returns

        if len(returns) < 2:
            return 0.0

        avg_return = sum(returns) / len(returns)
        daily_rf = self.RISK_FREE_RATE / self.TRADING_DAYS_PER_YEAR
        excess_return = avg_return - daily_rf

        # 只计算负收益的标准差
        negative_returns = [r for r in returns if r < 0]
        if not negative_returns:
            return float('inf') if excess_return > 0 else 0.0

        downside_variance = sum(r ** 2 for r in negative_returns) / len(returns)
        downside_std = math.sqrt(downside_variance)

        if downside_std == 0:
            return 0.0

        sortino = (excess_return / downside_std) * math.sqrt(self.TRADING_DAYS_PER_YEAR)
        return sortino

    def calculate_max_drawdown(self) -> Tuple[float, int]:
        """
        计算最大回撤和持续时间
        """
        if not self._equity_curve:
            return 0.0, 0

        peak = self.initial_equity
        max_dd = 0.0
        max_dd_duration = 0
        current_dd_start = None

        for timestamp, equity in self._equity_curve:
            if equity > peak:
                peak = equity
                current_dd_start = None
            else:
                dd = (peak - equity) / peak
                if dd > max_dd:
                    max_dd = dd

                if current_dd_start is None:
                    current_dd_start = timestamp
                else:
                    duration = (timestamp - current_dd_start).days
                    if duration > max_dd_duration:
                        max_dd_duration = duration

        return max_dd, max_dd_duration

    def calculate_volatility(self, returns: List[float] = None) -> float:
        """计算年化波动率"""
        if returns is None:
            returns = self._daily_returns

        if len(returns) < 2:
            return 0.0

        avg_return = sum(returns) / len(returns)
        variance = sum((r - avg_return) ** 2 for r in returns) / len(returns)
        daily_vol = math.sqrt(variance)

        # 年化
        annual_vol = daily_vol * math.sqrt(self.TRADING_DAYS_PER_YEAR)
        return annual_vol

    def calculate_profit_factor(self) -> float:
        """计算盈亏比"""
        gross_profit = sum(t.net_pnl for t in self._trades if t.net_pnl > 0)
        gross_loss = abs(sum(t.net_pnl for t in self._trades if t.net_pnl < 0))

        if gross_loss == 0:
            return float('inf') if gross_profit > 0 else 0.0

        return gross_profit / gross_loss

    def get_performance_metrics(self) -> PerformanceMetrics:
        """获取完整绩效指标"""
        with self._lock:
            # 确保当日统计被包含
            returns = self._daily_returns.copy()
            if self._today_stats:
                returns.append(self._today_stats.daily_return)

            # 基本统计
            closed_trades = [t for t in self._trades if t.is_closed]
            winning_trades = [t for t in closed_trades if t.net_pnl > 0]
            losing_trades = [t for t in closed_trades if t.net_pnl < 0]

            # 计算收益
            total_return = (self.current_equity - self.initial_equity) / self.initial_equity
            trading_days = max(1, len(returns))
            annualized_return = ((1 + total_return) ** (self.TRADING_DAYS_PER_YEAR / trading_days)) - 1

            # 计算风险指标
            max_dd, max_dd_duration = self.calculate_max_drawdown()

            # 计算成交率
            fill_rate = self._orders_filled / max(1, self._orders_submitted)

            # 计算平均滑点
            avg_slippage = self._total_slippage / max(1, self._orders_filled)

            # 计算平均持仓时间
            holding_times = [t.holding_time.total_seconds() / 3600
                           for t in closed_trades if t.holding_time]
            avg_holding_time = sum(holding_times) / max(1, len(holding_times))

            # 计算日均成交额
            total_volume = sum(s.total_volume for s in self._daily_stats)
            if self._today_stats:
                total_volume += self._today_stats.total_volume
            avg_daily_volume = total_volume / max(1, trading_days)

            metrics = PerformanceMetrics(
                # 收益
                total_return=total_return,
                annualized_return=annualized_return,

                # 风险
                sharpe_ratio=self.calculate_sharpe_ratio(returns),
                sortino_ratio=self.calculate_sortino_ratio(returns),
                max_drawdown=max_dd,
                max_drawdown_duration=max_dd_duration,
                volatility=self.calculate_volatility(returns),

                # 交易
                total_trades=len(closed_trades),
                winning_trades=len(winning_trades),
                losing_trades=len(losing_trades),
                win_rate=len(winning_trades) / max(1, len(closed_trades)),
                profit_factor=self.calculate_profit_factor(),
                avg_win=sum(t.net_pnl for t in winning_trades) / max(1, len(winning_trades)),
                avg_loss=sum(t.net_pnl for t in losing_trades) / max(1, len(losing_trades)),
                avg_trade=sum(t.net_pnl for t in closed_trades) / max(1, len(closed_trades)),

                # 成交
                total_volume=total_volume,
                avg_daily_volume=avg_daily_volume,
                fill_rate=fill_rate,
                avg_slippage=avg_slippage,

                # 时间
                trading_days=trading_days,
                avg_holding_time=avg_holding_time
            )

            return metrics

    def get_daily_stats(self) -> List[Dict[str, Any]]:
        """获取每日统计"""
        with self._lock:
            stats = [s.to_dict() for s in self._daily_stats]
            if self._today_stats:
                stats.append(self._today_stats.to_dict())
            return stats

    def get_trades(self, last_n: int = None) -> List[Dict[str, Any]]:
        """获取交易记录"""
        with self._lock:
            trades = self._trades if last_n is None else self._trades[-last_n:]
            return [t.to_dict() for t in trades]

    def get_equity_curve(self) -> List[Dict[str, Any]]:
        """获取权益曲线"""
        with self._lock:
            return [
                {"timestamp": ts.isoformat(), "equity": equity}
                for ts, equity in self._equity_curve
            ]

    def save_to_file(self, filepath: str):
        """保存绩效数据到文件"""
        data = {
            "metrics": self.get_performance_metrics().to_dict(),
            "daily_stats": self.get_daily_stats(),
            "trades": self.get_trades(),
            "equity_curve": self.get_equity_curve()
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info(f"Performance data saved to {filepath}")

    def reset(self, initial_equity: float = None):
        """重置分析器"""
        with self._lock:
            if initial_equity:
                self.initial_equity = initial_equity
            self.current_equity = self.initial_equity
            self._trades.clear()
            self._daily_stats.clear()
            self._daily_returns.clear()
            self._equity_curve.clear()
            self._orders_submitted = 0
            self._orders_filled = 0
            self._orders_rejected = 0
            self._total_slippage = 0.0
            self._today_stats = None
            self._high_watermark = self.initial_equity


# 全局单例
_performance_analyzer: Optional[PerformanceAnalyzer] = None


def get_performance_analyzer(initial_equity: float = 50000.0) -> PerformanceAnalyzer:
    """获取绩效分析器单例"""
    global _performance_analyzer
    if _performance_analyzer is None:
        _performance_analyzer = PerformanceAnalyzer(initial_equity)
    return _performance_analyzer
