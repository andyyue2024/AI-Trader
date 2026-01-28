# -*- coding: utf-8 -*-
"""
高级回放模块
支持分钟级时间精度和实时回放
"""

import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Any, Callable, Dict, Generator, List, Optional
import threading

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ReplayConfig:
    """回放配置"""
    start_datetime: datetime = None
    end_datetime: datetime = None
    speed: float = 1.0  # 回放速度倍数
    interval: str = "1min"  # 时间间隔: 1min, 5min, 15min, 1hour, 1day
    symbols: List[str] = field(default_factory=lambda: ["TQQQ", "QQQ"])
    data_dir: str = "./data"
    realtime_mode: bool = False  # 实时模式（模拟实际时间流逝）

    def __post_init__(self):
        if self.start_datetime is None:
            self.start_datetime = datetime.now() - timedelta(days=30)
        if self.end_datetime is None:
            self.end_datetime = datetime.now()


@dataclass
class MarketTick:
    """市场 Tick 数据"""
    timestamp: datetime
    symbol: str
    price: float
    volume: float = 0.0
    bid: float = 0.0
    ask: float = 0.0
    open: float = 0.0
    high: float = 0.0
    low: float = 0.0
    close: float = 0.0

    def to_dict(self) -> Dict:
        return {
            "timestamp": self.timestamp.isoformat(),
            "symbol": self.symbol,
            "price": self.price,
            "volume": self.volume,
            "bid": self.bid,
            "ask": self.ask,
            "ohlc": {
                "open": self.open,
                "high": self.high,
                "low": self.low,
                "close": self.close
            }
        }


class MarketDataLoader:
    """市场数据加载器"""

    def __init__(self, data_dir: str = "./data"):
        self.data_dir = Path(data_dir)
        self.cache: Dict[str, List[Dict]] = {}

    def load_daily_data(self, symbol: str) -> List[Dict]:
        """加载日线数据"""
        if symbol in self.cache:
            return self.cache[symbol]

        filepath = self.data_dir / f"daily_prices_{symbol}.json"
        if not filepath.exists():
            logger.warning(f"Data file not found: {filepath}")
            return []

        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        self.cache[symbol] = data
        return data

    def load_intraday_data(self, symbol: str, interval: str = "1min") -> List[Dict]:
        """加载日内数据"""
        # 首先检查是否有日内数据文件
        filepath = self.data_dir / f"intraday_{interval}_{symbol}.json"
        if filepath.exists():
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)

        # 否则从日线数据模拟生成
        daily_data = self.load_daily_data(symbol)
        return self._simulate_intraday(daily_data, interval)

    def _simulate_intraday(self, daily_data: List[Dict], interval: str) -> List[Dict]:
        """从日线数据模拟生成日内数据"""
        intraday = []

        intervals_per_day = {
            "1min": 390,   # 6.5小时 * 60分钟
            "5min": 78,
            "15min": 26,
            "30min": 13,
            "1hour": 7
        }

        n_intervals = intervals_per_day.get(interval, 390)

        for day in daily_data:
            try:
                date_str = day.get("date", "")
                open_price = float(day.get("1. open") or day.get("open", 0))
                high_price = float(day.get("2. high") or day.get("high", 0))
                low_price = float(day.get("3. low") or day.get("low", 0))
                close_price = float(day.get("4. close") or day.get("close", 0))
                volume = float(day.get("5. volume") or day.get("volume", 0))

                if not date_str or open_price == 0:
                    continue

                # 生成日内 K 线
                base_dt = datetime.strptime(date_str, "%Y-%m-%d").replace(hour=9, minute=30)
                price_range = high_price - low_price

                for i in range(n_intervals):
                    # 简单线性插值模拟
                    progress = i / n_intervals

                    # 价格走势：开盘 -> 日内波动 -> 收盘
                    if progress < 0.1:
                        price = open_price + (high_price - open_price) * (progress / 0.1) * 0.5
                    elif progress < 0.5:
                        price = open_price + (high_price - open_price) * 0.5
                    elif progress < 0.7:
                        price = high_price - (high_price - low_price) * ((progress - 0.5) / 0.2)
                    else:
                        price = low_price + (close_price - low_price) * ((progress - 0.7) / 0.3)

                    # 添加一些随机波动
                    import random
                    noise = random.uniform(-0.001, 0.001) * price
                    price += noise

                    # 计算时间戳
                    if interval == "1min":
                        ts = base_dt + timedelta(minutes=i)
                    elif interval == "5min":
                        ts = base_dt + timedelta(minutes=i * 5)
                    elif interval == "15min":
                        ts = base_dt + timedelta(minutes=i * 15)
                    elif interval == "30min":
                        ts = base_dt + timedelta(minutes=i * 30)
                    else:  # 1hour
                        ts = base_dt + timedelta(hours=i)

                    intraday.append({
                        "timestamp": ts.isoformat(),
                        "symbol": day.get("symbol", ""),
                        "open": price,
                        "high": price * 1.001,
                        "low": price * 0.999,
                        "close": price,
                        "volume": volume / n_intervals
                    })
            except Exception as e:
                logger.error(f"Error simulating intraday data: {e}")
                continue

        return intraday


class AdvancedReplayEngine:
    """高级回放引擎"""

    def __init__(self, config: ReplayConfig = None):
        self.config = config or ReplayConfig()
        self.loader = MarketDataLoader(self.config.data_dir)

        self.current_time: datetime = self.config.start_datetime
        self.is_running = False
        self.is_paused = False

        # 回调函数
        self.on_tick: Optional[Callable[[MarketTick], None]] = None
        self.on_bar: Optional[Callable[[Dict], None]] = None
        self.on_day_end: Optional[Callable[[date], None]] = None

        # 数据缓存
        self.market_data: Dict[str, List[Dict]] = {}
        self.current_index: Dict[str, int] = {}

    def load_data(self) -> bool:
        """加载回放数据"""
        logger.info(f"Loading replay data for {self.config.symbols}...")

        for symbol in self.config.symbols:
            if self.config.interval in ["1min", "5min", "15min", "30min", "1hour"]:
                data = self.loader.load_intraday_data(symbol, self.config.interval)
            else:
                data = self.loader.load_daily_data(symbol)

            if data:
                # 过滤时间范围
                filtered = []
                for record in data:
                    try:
                        ts_str = record.get("timestamp") or record.get("date", "")
                        if "T" in ts_str:
                            ts = datetime.fromisoformat(ts_str.replace("Z", ""))
                        else:
                            ts = datetime.strptime(ts_str, "%Y-%m-%d")

                        if self.config.start_datetime <= ts <= self.config.end_datetime:
                            record["_timestamp"] = ts
                            filtered.append(record)
                    except:
                        continue

                self.market_data[symbol] = sorted(filtered, key=lambda x: x["_timestamp"])
                self.current_index[symbol] = 0
                logger.info(f"  {symbol}: {len(filtered)} records")

        return len(self.market_data) > 0

    def get_current_tick(self, symbol: str) -> Optional[MarketTick]:
        """获取当前 Tick"""
        if symbol not in self.market_data:
            return None

        idx = self.current_index.get(symbol, 0)
        data = self.market_data[symbol]

        if idx >= len(data):
            return None

        record = data[idx]
        return MarketTick(
            timestamp=record["_timestamp"],
            symbol=symbol,
            price=float(record.get("close", 0)),
            volume=float(record.get("volume", 0)),
            open=float(record.get("open", 0)),
            high=float(record.get("high", 0)),
            low=float(record.get("low", 0)),
            close=float(record.get("close", 0))
        )

    def step(self) -> Dict[str, MarketTick]:
        """前进一步"""
        ticks = {}

        for symbol in self.config.symbols:
            tick = self.get_current_tick(symbol)
            if tick:
                ticks[symbol] = tick
                self.current_index[symbol] = self.current_index.get(symbol, 0) + 1

                # 触发回调
                if self.on_tick:
                    self.on_tick(tick)

        if ticks:
            self.current_time = max(t.timestamp for t in ticks.values())

            # 触发 bar 回调
            if self.on_bar:
                bar_data = {s: t.to_dict() for s, t in ticks.items()}
                self.on_bar(bar_data)

        return ticks

    def run(self) -> Generator[Dict[str, MarketTick], None, None]:
        """运行回放（生成器模式）"""
        if not self.load_data():
            logger.error("Failed to load data")
            return

        self.is_running = True
        last_date = None

        while self.is_running:
            if self.is_paused:
                time.sleep(0.1)
                continue

            ticks = self.step()

            if not ticks:
                # 所有数据回放完成
                break

            yield ticks

            # 检查日期变化
            current_date = self.current_time.date()
            if last_date and current_date != last_date:
                if self.on_day_end:
                    self.on_day_end(last_date)
            last_date = current_date

            # 实时模式：模拟时间流逝
            if self.config.realtime_mode:
                sleep_time = self._get_interval_seconds() / self.config.speed
                time.sleep(sleep_time)

        self.is_running = False
        logger.info("Replay completed")

    def _get_interval_seconds(self) -> float:
        """获取间隔秒数"""
        intervals = {
            "1min": 60,
            "5min": 300,
            "15min": 900,
            "30min": 1800,
            "1hour": 3600,
            "1day": 86400
        }
        return intervals.get(self.config.interval, 60)

    def pause(self):
        """暂停回放"""
        self.is_paused = True
        logger.info("Replay paused")

    def resume(self):
        """恢复回放"""
        self.is_paused = False
        logger.info("Replay resumed")

    def stop(self):
        """停止回放"""
        self.is_running = False
        logger.info("Replay stopped")

    def set_speed(self, speed: float):
        """设置回放速度"""
        self.config.speed = max(0.1, min(100.0, speed))
        logger.info(f"Replay speed set to {self.config.speed}x")

    def seek(self, target_time: datetime):
        """跳转到指定时间"""
        for symbol in self.config.symbols:
            data = self.market_data.get(symbol, [])
            for i, record in enumerate(data):
                if record["_timestamp"] >= target_time:
                    self.current_index[symbol] = i
                    break

        self.current_time = target_time
        logger.info(f"Seeked to {target_time}")


class ReplayController:
    """回放控制器（支持多线程）"""

    def __init__(self, engine: AdvancedReplayEngine):
        self.engine = engine
        self.thread: Optional[threading.Thread] = None
        self.tick_handlers: List[Callable[[MarketTick], None]] = []

    def add_tick_handler(self, handler: Callable[[MarketTick], None]):
        """添加 Tick 处理器"""
        self.tick_handlers.append(handler)

    def _run_loop(self):
        """后台运行循环"""
        for ticks in self.engine.run():
            for tick in ticks.values():
                for handler in self.tick_handlers:
                    try:
                        handler(tick)
                    except Exception as e:
                        logger.error(f"Tick handler error: {e}")

    def start_async(self):
        """异步启动回放"""
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        logger.info("Replay started in background")

    def wait(self):
        """等待回放完成"""
        if self.thread:
            self.thread.join()


def run_replay(
    symbols: List[str] = None,
    start_date: str = None,
    end_date: str = None,
    interval: str = "1min",
    speed: float = 1.0,
    on_tick: Callable = None
) -> AdvancedReplayEngine:
    """便捷回放函数"""
    config = ReplayConfig(
        symbols=symbols or ["TQQQ", "QQQ"],
        interval=interval,
        speed=speed
    )

    if start_date:
        config.start_datetime = datetime.strptime(start_date, "%Y-%m-%d")
    if end_date:
        config.end_datetime = datetime.strptime(end_date, "%Y-%m-%d")

    engine = AdvancedReplayEngine(config)
    engine.on_tick = on_tick

    return engine


if __name__ == "__main__":
    # 示例使用
    def print_tick(tick: MarketTick):
        print(f"[{tick.timestamp}] {tick.symbol}: ${tick.price:.2f} (Vol: {tick.volume:,.0f})")

    engine = run_replay(
        symbols=["AAPL", "MSFT"],
        start_date="2024-01-01",
        end_date="2024-01-05",
        interval="1hour",
        on_tick=print_tick
    )

    # 运行回放
    count = 0
    for ticks in engine.run():
        count += 1
        if count >= 10:  # 只回放前 10 个
            break

    print(f"\nReplayed {count} ticks")
