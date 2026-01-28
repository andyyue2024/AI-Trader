# -*- coding: utf-8 -*-
"""
Futu 实时行情订阅器
支持1分钟K线、逐笔、盘口数据
支持盘前/盘后/夜盘连续交易
"""

import asyncio
import logging
import os
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
from queue import Queue

try:
    from futu import (
        OpenQuoteContext, RET_OK, RET_ERROR,
        SubType, KLType, AuType,
        StockQuoteHandlerBase, OrderBookHandlerBase,
        CurKlineHandlerBase, TickerHandlerBase
    )
    FUTU_AVAILABLE = True
except ImportError:
    FUTU_AVAILABLE = False
    RET_OK, RET_ERROR = 0, -1
    class SubType:
        QUOTE = "QUOTE"
        ORDER_BOOK = "ORDER_BOOK"
        K_1M = "K_1M"
        K_5M = "K_5M"
        TICKER = "TICKER"
    class KLType:
        K_1M = "K_1M"
        K_5M = "K_5M"
        K_15M = "K_15M"
        K_60M = "K_60M"
        K_DAY = "K_DAY"

from .opend_client import OpenDClient, OpenDConnectionPool, get_default_pool, OpenDConfig

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MarketSession(Enum):
    """交易时段"""
    PRE_MARKET = "pre_market"       # 盘前 04:00-09:30 ET
    REGULAR = "regular"              # 正常 09:30-16:00 ET
    AFTER_HOURS = "after_hours"     # 盘后 16:00-20:00 ET
    OVERNIGHT = "overnight"          # 夜盘 (futures only)
    CLOSED = "closed"


@dataclass
class QuoteData:
    """行情数据"""
    symbol: str
    last_price: float
    open_price: float
    high_price: float
    low_price: float
    volume: int
    turnover: float
    bid_price: float = 0.0
    ask_price: float = 0.0
    bid_volume: int = 0
    ask_volume: int = 0
    timestamp: datetime = field(default_factory=datetime.now)
    session: MarketSession = MarketSession.REGULAR

    @property
    def spread(self) -> float:
        """买卖价差"""
        if self.bid_price > 0 and self.ask_price > 0:
            return (self.ask_price - self.bid_price) / self.bid_price
        return 0.0

    @property
    def mid_price(self) -> float:
        """中间价"""
        if self.bid_price > 0 and self.ask_price > 0:
            return (self.bid_price + self.ask_price) / 2
        return self.last_price

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "last_price": self.last_price,
            "open_price": self.open_price,
            "high_price": self.high_price,
            "low_price": self.low_price,
            "volume": self.volume,
            "turnover": self.turnover,
            "bid_price": self.bid_price,
            "ask_price": self.ask_price,
            "bid_volume": self.bid_volume,
            "ask_volume": self.ask_volume,
            "spread": round(self.spread, 6),
            "timestamp": self.timestamp.isoformat(),
            "session": self.session.value
        }


@dataclass
class KLineData:
    """K线数据"""
    symbol: str
    kl_type: str  # K_1M, K_5M, etc.
    time_key: str
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    volume: int
    turnover: float
    change_rate: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "kl_type": self.kl_type,
            "time_key": self.time_key,
            "open": self.open_price,
            "high": self.high_price,
            "low": self.low_price,
            "close": self.close_price,
            "volume": self.volume,
            "turnover": self.turnover,
            "change_rate": round(self.change_rate, 4)
        }


class FutuQuoteSubscriber:
    """
    富途行情订阅器
    支持实时行情推送和历史数据获取
    """

    def __init__(
        self,
        pool: Optional[OpenDConnectionPool] = None,
        symbols: Optional[List[str]] = None
    ):
        self.pool = pool or get_default_pool()
        self._symbols: Set[str] = set(symbols or [])
        self._quote_cache: Dict[str, QuoteData] = {}
        self._kline_cache: Dict[str, Dict[str, List[KLineData]]] = defaultdict(lambda: defaultdict(list))
        self._callbacks: Dict[str, List[Callable]] = defaultdict(list)
        self._running = False
        self._lock = threading.Lock()
        self._quote_thread: Optional[threading.Thread] = None

    def add_symbols(self, symbols: List[str]):
        """添加订阅标的"""
        self._symbols.update(symbols)

    def remove_symbols(self, symbols: List[str]):
        """移除订阅标的"""
        self._symbols -= set(symbols)

    def _to_futu_symbols(self, symbols: List[str]) -> List[str]:
        """转换为富途格式"""
        return [f"US.{s}" if "." not in s else s for s in symbols]

    def register_callback(
        self,
        event: str,  # "quote", "kline", "ticker"
        callback: Callable
    ):
        """注册回调"""
        self._callbacks[event].append(callback)

    def _notify(self, event: str, data: Any):
        """通知回调"""
        for cb in self._callbacks.get(event, []):
            try:
                cb(data)
            except Exception as e:
                logger.error(f"Callback error for {event}: {e}")

    def get_current_session(self) -> MarketSession:
        """获取当前交易时段 (Eastern Time)"""
        # 简化实现，实际需要考虑节假日等
        from datetime import timezone
        try:
            import pytz
            et = pytz.timezone('US/Eastern')
            now = datetime.now(et)
        except ImportError:
            # Fallback: 使用 UTC-5 近似东部时间
            now = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=5)

        hour = now.hour
        minute = now.minute
        weekday = now.weekday()

        # 周末
        if weekday >= 5:
            return MarketSession.CLOSED

        # 盘前 04:00-09:30
        if (hour == 4 and minute >= 0) or (4 < hour < 9) or (hour == 9 and minute < 30):
            return MarketSession.PRE_MARKET
        # 正常 09:30-16:00
        elif (hour == 9 and minute >= 30) or (9 < hour < 16):
            return MarketSession.REGULAR
        # 盘后 16:00-20:00
        elif 16 <= hour < 20:
            return MarketSession.AFTER_HOURS
        else:
            return MarketSession.CLOSED

    async def get_quote(self, symbol: str, use_cache: bool = True) -> Optional[QuoteData]:
        """获取实时行情"""
        if use_cache and symbol in self._quote_cache:
            cached = self._quote_cache[symbol]
            # 缓存10秒有效
            if (datetime.now() - cached.timestamp).total_seconds() < 10:
                return cached

        futu_symbol = self._to_futu_symbols([symbol])[0]

        if not FUTU_AVAILABLE:
            # Mock data
            import random
            base_prices = {
                "TQQQ": 75.0, "QQQ": 490.0, "SOXL": 30.0,
                "SPXL": 180.0, "AAPL": 230.0
            }
            base = base_prices.get(symbol, 100.0)
            price = base * (1 + random.uniform(-0.005, 0.005))
            quote = QuoteData(
                symbol=symbol,
                last_price=price,
                open_price=base,
                high_price=price * 1.01,
                low_price=price * 0.99,
                volume=random.randint(100000, 1000000),
                turnover=price * random.randint(100000, 1000000),
                bid_price=price * 0.9999,
                ask_price=price * 1.0001,
                bid_volume=random.randint(100, 1000),
                ask_volume=random.randint(100, 1000),
                session=self.get_current_session()
            )
            with self._lock:
                self._quote_cache[symbol] = quote
            return quote

        try:
            with self.pool.get_connection() as client:
                ret, data = client.quote_ctx.get_market_snapshot([futu_symbol])
                if ret == RET_OK and len(data) > 0:
                    row = data.iloc[0]
                    quote = QuoteData(
                        symbol=symbol,
                        last_price=float(row['last_price']),
                        open_price=float(row.get('open_price', 0)),
                        high_price=float(row.get('high_price', 0)),
                        low_price=float(row.get('low_price', 0)),
                        volume=int(row.get('volume', 0)),
                        turnover=float(row.get('turnover', 0)),
                        session=self.get_current_session()
                    )
                    with self._lock:
                        self._quote_cache[symbol] = quote
                    return quote
        except Exception as e:
            logger.error(f"Failed to get quote for {symbol}: {e}")

        return None

    async def get_klines(
        self,
        symbol: str,
        kl_type: str = "K_1M",
        count: int = 100,
        use_cache: bool = True
    ) -> List[KLineData]:
        """获取K线数据"""
        cache_key = f"{symbol}_{kl_type}"

        if use_cache and cache_key in self._kline_cache:
            cached = self._kline_cache[symbol][kl_type]
            if len(cached) >= count:
                return cached[-count:]

        futu_symbol = self._to_futu_symbols([symbol])[0]

        if not FUTU_AVAILABLE:
            # Mock K-line data
            import random
            klines = []
            base_price = {"TQQQ": 75.0, "QQQ": 490.0}.get(symbol, 100.0)

            for i in range(count):
                time_key = (datetime.now() - timedelta(minutes=count-i)).strftime("%Y-%m-%d %H:%M:00")
                price_change = random.uniform(-0.005, 0.005)
                open_p = base_price * (1 + random.uniform(-0.003, 0.003))
                close_p = open_p * (1 + price_change)
                high_p = max(open_p, close_p) * (1 + random.uniform(0, 0.002))
                low_p = min(open_p, close_p) * (1 - random.uniform(0, 0.002))

                klines.append(KLineData(
                    symbol=symbol,
                    kl_type=kl_type,
                    time_key=time_key,
                    open_price=round(open_p, 2),
                    high_price=round(high_p, 2),
                    low_price=round(low_p, 2),
                    close_price=round(close_p, 2),
                    volume=random.randint(10000, 100000),
                    turnover=close_p * random.randint(10000, 100000),
                    change_rate=price_change
                ))
                base_price = close_p

            with self._lock:
                self._kline_cache[symbol][kl_type] = klines
            return klines

        try:
            with self.pool.get_connection() as client:
                kl_type_enum = getattr(KLType, kl_type, KLType.K_1M)
                ret, data, _ = client.quote_ctx.request_history_kline(
                    code=futu_symbol,
                    ktype=kl_type_enum,
                    max_count=count
                )

                if ret == RET_OK:
                    klines = []
                    for _, row in data.iterrows():
                        klines.append(KLineData(
                            symbol=symbol,
                            kl_type=kl_type,
                            time_key=row['time_key'],
                            open_price=float(row['open']),
                            high_price=float(row['high']),
                            low_price=float(row['low']),
                            close_price=float(row['close']),
                            volume=int(row['volume']),
                            turnover=float(row.get('turnover', 0)),
                            change_rate=float(row.get('change_rate', 0))
                        ))
                    with self._lock:
                        self._kline_cache[symbol][kl_type] = klines
                    return klines
        except Exception as e:
            logger.error(f"Failed to get klines for {symbol}: {e}")

        return []

    async def subscribe(self, symbols: Optional[List[str]] = None):
        """订阅实时行情"""
        symbols = symbols or list(self._symbols)
        if not symbols:
            logger.warning("No symbols to subscribe")
            return False

        futu_symbols = self._to_futu_symbols(symbols)

        if not FUTU_AVAILABLE:
            logger.info(f"[MOCK] Subscribed to {symbols}")
            self._running = True
            return True

        try:
            with self.pool.get_connection() as client:
                # 订阅行情
                ret, err = client.quote_ctx.subscribe(
                    futu_symbols,
                    [SubType.QUOTE, SubType.ORDER_BOOK, SubType.K_1M]
                )
                if ret != RET_OK:
                    logger.error(f"Subscribe failed: {err}")
                    return False

                logger.info(f"Subscribed to {symbols}")
                self._running = True
                return True
        except Exception as e:
            logger.error(f"Subscribe error: {e}")
            return False

    async def unsubscribe(self, symbols: Optional[List[str]] = None):
        """取消订阅"""
        symbols = symbols or list(self._symbols)
        futu_symbols = self._to_futu_symbols(symbols)

        if not FUTU_AVAILABLE:
            logger.info(f"[MOCK] Unsubscribed from {symbols}")
            return True

        try:
            with self.pool.get_connection() as client:
                ret, err = client.quote_ctx.unsubscribe(
                    futu_symbols,
                    [SubType.QUOTE, SubType.ORDER_BOOK, SubType.K_1M]
                )
                if ret != RET_OK:
                    logger.error(f"Unsubscribe failed: {err}")
                    return False
                return True
        except Exception as e:
            logger.error(f"Unsubscribe error: {e}")
            return False

    def start_streaming(self, interval: float = 1.0):
        """启动流式数据推送"""
        if self._quote_thread and self._quote_thread.is_alive():
            return

        self._running = True
        self._quote_thread = threading.Thread(
            target=self._streaming_loop,
            args=(interval,),
            daemon=True
        )
        self._quote_thread.start()
        logger.info("Quote streaming started")

    def stop_streaming(self):
        """停止流式数据"""
        self._running = False
        if self._quote_thread:
            self._quote_thread.join(timeout=5)
        logger.info("Quote streaming stopped")

    def _streaming_loop(self, interval: float):
        """流式数据循环"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        while self._running:
            try:
                for symbol in list(self._symbols):
                    quote = loop.run_until_complete(self.get_quote(symbol, use_cache=False))
                    if quote:
                        self._notify("quote", quote)
                time.sleep(interval)
            except Exception as e:
                logger.error(f"Streaming error: {e}")
                time.sleep(1)

        loop.close()

    def get_all_quotes(self) -> Dict[str, QuoteData]:
        """获取所有缓存的行情"""
        with self._lock:
            return dict(self._quote_cache)

    async def close(self):
        """关闭订阅器"""
        self.stop_streaming()
        await self.unsubscribe()
