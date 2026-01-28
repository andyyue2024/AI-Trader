# -*- coding: utf-8 -*-
"""
回测引擎
支持历史数据回测，验证策略有效性
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class BacktestConfig:
    """回测配置"""
    initial_capital: float = 50000.0
    start_date: date = None
    end_date: date = None
    symbols: List[str] = field(default_factory=lambda: ["TQQQ", "QQQ"])
    commission: float = 0.0  # 佣金比例
    slippage: float = 0.001  # 滑点 0.1%
    data_dir: str = "./data"
    enable_shorting: bool = True
    max_position_pct: float = 0.25  # 单标的最大仓位

    def __post_init__(self):
        if self.start_date is None:
            self.start_date = date.today() - timedelta(days=365)
        if self.end_date is None:
            self.end_date = date.today()


@dataclass
class Position:
    """持仓"""
    symbol: str
    quantity: int
    avg_cost: float
    side: str  # long/short
    entry_time: datetime = None

    @property
    def market_value(self) -> float:
        return abs(self.quantity) * self.avg_cost

    def update_pnl(self, current_price: float) -> float:
        if self.side == "long":
            return (current_price - self.avg_cost) * self.quantity
        else:
            return (self.avg_cost - current_price) * abs(self.quantity)


@dataclass
class Trade:
    """交易记录"""
    timestamp: datetime
    symbol: str
    side: str  # long/short/flat
    quantity: int
    price: float
    commission: float = 0.0
    slippage: float = 0.0
    pnl: float = 0.0

    def to_dict(self) -> Dict:
        return {
            "timestamp": self.timestamp.isoformat(),
            "symbol": self.symbol,
            "side": self.side,
            "quantity": self.quantity,
            "price": self.price,
            "commission": self.commission,
            "slippage": self.slippage,
            "pnl": self.pnl
        }


@dataclass
class BacktestResult:
    """回测结果"""
    config: BacktestConfig
    trades: List[Trade] = field(default_factory=list)
    equity_curve: List[Dict] = field(default_factory=list)
    daily_returns: List[float] = field(default_factory=list)

    # 绩效指标
    total_return: float = 0.0
    annual_return: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    max_drawdown: float = 0.0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    total_trades: int = 0
    avg_trade_pnl: float = 0.0
    avg_holding_period: float = 0.0

    def calculate_metrics(self):
        """计算所有绩效指标"""
        import math

        if not self.equity_curve:
            return

        # 总收益
        initial = self.equity_curve[0]["equity"]
        final = self.equity_curve[-1]["equity"]
        self.total_return = (final - initial) / initial

        # 年化收益
        days = (self.config.end_date - self.config.start_date).days
        if days > 0:
            self.annual_return = (1 + self.total_return) ** (365 / days) - 1

        # 日收益率
        if len(self.equity_curve) > 1:
            for i in range(1, len(self.equity_curve)):
                prev = self.equity_curve[i-1]["equity"]
                curr = self.equity_curve[i]["equity"]
                self.daily_returns.append((curr - prev) / prev)

        # 夏普比率
        if self.daily_returns:
            avg_return = sum(self.daily_returns) / len(self.daily_returns)
            std_return = math.sqrt(sum((r - avg_return) ** 2 for r in self.daily_returns) / len(self.daily_returns))
            if std_return > 0:
                self.sharpe_ratio = (avg_return * 252) / (std_return * math.sqrt(252))

        # 索提诺比率
        negative_returns = [r for r in self.daily_returns if r < 0]
        if negative_returns:
            downside_std = math.sqrt(sum(r ** 2 for r in negative_returns) / len(negative_returns))
            if downside_std > 0:
                avg_return = sum(self.daily_returns) / len(self.daily_returns)
                self.sortino_ratio = (avg_return * 252) / (downside_std * math.sqrt(252))

        # 最大回撤
        peak = self.equity_curve[0]["equity"]
        max_dd = 0
        for point in self.equity_curve:
            if point["equity"] > peak:
                peak = point["equity"]
            dd = (peak - point["equity"]) / peak
            if dd > max_dd:
                max_dd = dd
        self.max_drawdown = max_dd

        # 胜率和盈亏比
        if self.trades:
            self.total_trades = len(self.trades)
            winning = [t for t in self.trades if t.pnl > 0]
            losing = [t for t in self.trades if t.pnl < 0]

            self.win_rate = len(winning) / self.total_trades if self.total_trades > 0 else 0

            total_profit = sum(t.pnl for t in winning)
            total_loss = abs(sum(t.pnl for t in losing))
            self.profit_factor = total_profit / total_loss if total_loss > 0 else float('inf')

            self.avg_trade_pnl = sum(t.pnl for t in self.trades) / self.total_trades

    def to_dict(self) -> Dict:
        return {
            "config": {
                "initial_capital": self.config.initial_capital,
                "start_date": self.config.start_date.isoformat(),
                "end_date": self.config.end_date.isoformat(),
                "symbols": self.config.symbols
            },
            "metrics": {
                "total_return": round(self.total_return * 100, 2),
                "annual_return": round(self.annual_return * 100, 2),
                "sharpe_ratio": round(self.sharpe_ratio, 2),
                "sortino_ratio": round(self.sortino_ratio, 2),
                "max_drawdown": round(self.max_drawdown * 100, 2),
                "win_rate": round(self.win_rate * 100, 2),
                "profit_factor": round(self.profit_factor, 2),
                "total_trades": self.total_trades,
                "avg_trade_pnl": round(self.avg_trade_pnl, 2)
            },
            "trades_count": len(self.trades),
            "equity_points": len(self.equity_curve)
        }

    def print_summary(self):
        """打印回测摘要"""
        print("\n" + "=" * 60)
        print("  Backtest Results")
        print("=" * 60)
        print(f"  Period: {self.config.start_date} to {self.config.end_date}")
        print(f"  Symbols: {', '.join(self.config.symbols)}")
        print("-" * 60)
        print(f"  Total Return:     {self.total_return * 100:>10.2f}%")
        print(f"  Annual Return:    {self.annual_return * 100:>10.2f}%")
        print(f"  Sharpe Ratio:     {self.sharpe_ratio:>10.2f}  {'✓' if self.sharpe_ratio >= 2 else '✗'} (Target: ≥2)")
        print(f"  Sortino Ratio:    {self.sortino_ratio:>10.2f}")
        print(f"  Max Drawdown:     {self.max_drawdown * 100:>10.2f}%  {'✓' if self.max_drawdown <= 0.15 else '✗'} (Target: ≤15%)")
        print(f"  Win Rate:         {self.win_rate * 100:>10.2f}%")
        print(f"  Profit Factor:    {self.profit_factor:>10.2f}")
        print(f"  Total Trades:     {self.total_trades:>10}")
        print(f"  Avg Trade P&L:   ${self.avg_trade_pnl:>10.2f}")
        print("=" * 60)


class BacktestEngine:
    """回测引擎"""

    def __init__(self, config: BacktestConfig = None):
        self.config = config or BacktestConfig()
        self.positions: Dict[str, Position] = {}
        self.cash = self.config.initial_capital
        self.equity_history: List[Dict] = []
        self.trades: List[Trade] = []
        self.current_date: date = None
        self.market_data: Dict[str, List[Dict]] = {}

    def load_data(self) -> bool:
        """加载历史数据"""
        logger.info(f"Loading data for {self.config.symbols}...")

        for symbol in self.config.symbols:
            data_file = Path(self.config.data_dir) / f"daily_prices_{symbol}.json"

            if not data_file.exists():
                logger.warning(f"Data file not found: {data_file}")
                continue

            try:
                with open(data_file, 'r') as f:
                    data = json.load(f)

                # 过滤日期范围
                filtered = []
                for record in data:
                    try:
                        record_date = datetime.strptime(record["date"], "%Y-%m-%d").date()
                        if self.config.start_date <= record_date <= self.config.end_date:
                            filtered.append(record)
                    except:
                        continue

                self.market_data[symbol] = sorted(filtered, key=lambda x: x["date"])
                logger.info(f"  {symbol}: {len(filtered)} records")

            except Exception as e:
                logger.error(f"Failed to load {symbol}: {e}")

        return len(self.market_data) > 0

    def get_price(self, symbol: str, date_str: str) -> Optional[float]:
        """获取指定日期的收盘价"""
        if symbol not in self.market_data:
            return None

        for record in self.market_data[symbol]:
            if record["date"] == date_str:
                return record.get("4. close") or record.get("close")

        return None

    def get_equity(self) -> float:
        """计算当前权益"""
        equity = self.cash

        for symbol, pos in self.positions.items():
            if self.current_date:
                price = self.get_price(symbol, self.current_date.strftime("%Y-%m-%d"))
                if price:
                    if pos.side == "long":
                        equity += pos.quantity * price
                    else:
                        equity += pos.quantity * pos.avg_cost + (pos.avg_cost - price) * abs(pos.quantity)

        return equity

    def execute_trade(
        self,
        symbol: str,
        action: str,
        quantity: int,
        price: float,
        timestamp: datetime
    ) -> Trade:
        """执行交易"""
        # 计算滑点和佣金
        if action == "long":
            executed_price = price * (1 + self.config.slippage)
        elif action == "short":
            executed_price = price * (1 - self.config.slippage)
        else:
            executed_price = price

        commission = abs(quantity * executed_price * self.config.commission)
        slippage_cost = abs(quantity * price * self.config.slippage)

        pnl = 0.0

        # 处理持仓
        if action == "long":
            if symbol in self.positions and self.positions[symbol].side == "short":
                # 平空仓
                pos = self.positions[symbol]
                pnl = (pos.avg_cost - executed_price) * abs(pos.quantity)
                self.cash += pos.market_value + pnl
                del self.positions[symbol]

            # 开多仓
            cost = quantity * executed_price + commission
            if cost <= self.cash:
                self.cash -= cost
                self.positions[symbol] = Position(
                    symbol=symbol,
                    quantity=quantity,
                    avg_cost=executed_price,
                    side="long",
                    entry_time=timestamp
                )

        elif action == "short":
            if self.config.enable_shorting:
                if symbol in self.positions and self.positions[symbol].side == "long":
                    # 平多仓
                    pos = self.positions[symbol]
                    pnl = (executed_price - pos.avg_cost) * pos.quantity
                    self.cash += pos.quantity * executed_price + pnl - commission
                    del self.positions[symbol]

                # 开空仓
                self.positions[symbol] = Position(
                    symbol=symbol,
                    quantity=-quantity,
                    avg_cost=executed_price,
                    side="short",
                    entry_time=timestamp
                )

        elif action == "flat":
            if symbol in self.positions:
                pos = self.positions[symbol]
                if pos.side == "long":
                    pnl = (executed_price - pos.avg_cost) * pos.quantity
                    self.cash += pos.quantity * executed_price - commission
                else:
                    pnl = (pos.avg_cost - executed_price) * abs(pos.quantity)
                    self.cash += pos.market_value + pnl - commission
                del self.positions[symbol]

        trade = Trade(
            timestamp=timestamp,
            symbol=symbol,
            side=action,
            quantity=quantity,
            price=executed_price,
            commission=commission,
            slippage=slippage_cost,
            pnl=pnl
        )

        self.trades.append(trade)
        return trade

    def run(
        self,
        strategy: Callable[[Dict, Dict], Dict]
    ) -> BacktestResult:
        """
        运行回测

        Args:
            strategy: 策略函数，接收 (market_data, positions) 返回 {"symbol": "action", ...}
        """
        if not self.load_data():
            logger.error("Failed to load data")
            return BacktestResult(config=self.config)

        # 获取所有交易日
        all_dates = set()
        for symbol, data in self.market_data.items():
            for record in data:
                all_dates.add(record["date"])

        sorted_dates = sorted(all_dates)

        logger.info(f"Running backtest from {sorted_dates[0]} to {sorted_dates[-1]}...")

        for date_str in sorted_dates:
            self.current_date = datetime.strptime(date_str, "%Y-%m-%d").date()

            # 构建当日市场数据
            daily_data = {}
            for symbol in self.config.symbols:
                price = self.get_price(symbol, date_str)
                if price:
                    daily_data[symbol] = {
                        "date": date_str,
                        "price": price,
                        "symbol": symbol
                    }

            if not daily_data:
                continue

            # 调用策略
            try:
                signals = strategy(daily_data, self.positions)

                # 执行信号
                for symbol, action in signals.items():
                    if action and action != "hold":
                        price = daily_data.get(symbol, {}).get("price")
                        if price:
                            quantity = int(self.cash * self.config.max_position_pct / price)
                            if quantity > 0:
                                self.execute_trade(
                                    symbol=symbol,
                                    action=action,
                                    quantity=quantity,
                                    price=price,
                                    timestamp=datetime.combine(self.current_date, datetime.min.time())
                                )
            except Exception as e:
                logger.error(f"Strategy error on {date_str}: {e}")

            # 记录权益
            equity = self.get_equity()
            self.equity_history.append({
                "date": date_str,
                "equity": equity,
                "cash": self.cash,
                "positions": len(self.positions)
            })

        # 生成结果
        result = BacktestResult(
            config=self.config,
            trades=self.trades,
            equity_curve=self.equity_history
        )
        result.calculate_metrics()

        return result


def simple_momentum_strategy(market_data: Dict, positions: Dict) -> Dict:
    """简单动量策略示例"""
    signals = {}

    for symbol, data in market_data.items():
        # 这里应该有更复杂的逻辑，这只是示例
        if symbol not in positions:
            signals[symbol] = "long"
        else:
            signals[symbol] = "hold"

    return signals


def run_backtest(
    symbols: List[str] = None,
    start_date: str = None,
    end_date: str = None,
    initial_capital: float = 50000.0,
    strategy: Callable = None
) -> BacktestResult:
    """便捷回测函数"""
    config = BacktestConfig(
        symbols=symbols or ["TQQQ", "QQQ"],
        initial_capital=initial_capital
    )

    if start_date:
        config.start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
    if end_date:
        config.end_date = datetime.strptime(end_date, "%Y-%m-%d").date()

    engine = BacktestEngine(config)
    result = engine.run(strategy or simple_momentum_strategy)

    return result


if __name__ == "__main__":
    # 示例运行
    result = run_backtest(
        symbols=["AAPL", "MSFT"],
        start_date="2024-01-01",
        end_date="2024-12-31"
    )
    result.print_summary()
