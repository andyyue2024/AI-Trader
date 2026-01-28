# -*- coding: utf-8 -*-
"""
Futu 交易执行器
实现高频交易核心功能：long/short/flat
目标：下单延迟 ≤ 0.0014s，滑点 ≤ 0.2%
"""

import asyncio
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal, ROUND_DOWN
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
from concurrent.futures import ThreadPoolExecutor
import threading
import json

try:
    from futu import (
        RET_OK, RET_ERROR,
        TrdEnv, TrdMarket,
        OrderType as FutuOrderType,
        OrderStatus, TrdSide,
        ModifyOrderOp, TimeInForce
    )
    FUTU_AVAILABLE = True
except ImportError:
    FUTU_AVAILABLE = False
    RET_OK, RET_ERROR = 0, -1
    # Mock enums
    class FutuOrderType:
        MARKET = "MARKET"
        LIMIT = "LIMIT"
        SPECIAL_LIMIT = "SPECIAL_LIMIT"
    class TrdSide:
        BUY = "BUY"
        SELL = "SELL"
        SELL_SHORT = "SELL_SHORT"
        BUY_BACK = "BUY_BACK"
    class OrderStatus:
        SUBMITTED = "SUBMITTED"
        FILLED_ALL = "FILLED_ALL"
        CANCELLED_ALL = "CANCELLED_ALL"
        FAILED = "FAILED"

from .opend_client import OpenDClient, OpenDConnectionPool, get_default_pool, OpenDConfig

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class OrderType(Enum):
    """订单类型"""
    MARKET = "market"           # 市价单
    LIMIT = "limit"             # 限价单
    LIMIT_IF_TOUCHED = "LIT"    # 触发限价单
    MARKET_IF_TOUCHED = "MIT"   # 触发市价单
    TRAILING_STOP = "TRAIL"     # 追踪止损


class OrderSide(Enum):
    """交易方向"""
    LONG = "long"       # 做多（买入）
    SHORT = "short"     # 做空（卖空）
    FLAT = "flat"       # 平仓


class OrderState(Enum):
    """订单状态"""
    PENDING = "pending"
    SUBMITTED = "submitted"
    PARTIAL_FILLED = "partial_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    FAILED = "failed"


@dataclass
class OrderRequest:
    """订单请求"""
    symbol: str                     # 股票代码 (e.g., "US.TQQQ")
    side: OrderSide                 # 交易方向
    quantity: int                   # 数量
    order_type: OrderType = OrderType.MARKET  # 订单类型
    price: Optional[float] = None   # 限价（限价单时必填）
    stop_price: Optional[float] = None  # 止损价
    time_in_force: str = "DAY"      # 有效期: DAY/GTC/IOC/FOK
    client_order_id: Optional[str] = None  # 客户端订单ID

    def __post_init__(self):
        if self.client_order_id is None:
            self.client_order_id = f"ORD_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"


@dataclass
class OrderResult:
    """订单结果"""
    success: bool
    order_id: Optional[str] = None
    client_order_id: Optional[str] = None
    symbol: str = ""
    side: OrderSide = OrderSide.LONG
    quantity: int = 0
    filled_quantity: int = 0
    price: float = 0.0
    filled_price: float = 0.0
    state: OrderState = OrderState.PENDING
    commission: float = 0.0
    slippage: float = 0.0          # 滑点百分比
    latency_ms: float = 0.0        # 延迟(毫秒)
    error_message: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    raw_response: Optional[Dict] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "order_id": self.order_id,
            "client_order_id": self.client_order_id,
            "symbol": self.symbol,
            "side": self.side.value,
            "quantity": self.quantity,
            "filled_quantity": self.filled_quantity,
            "price": self.price,
            "filled_price": self.filled_price,
            "state": self.state.value,
            "commission": self.commission,
            "slippage": round(self.slippage, 4),
            "latency_ms": round(self.latency_ms, 3),
            "error_message": self.error_message,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class Position:
    """持仓信息"""
    symbol: str
    quantity: int                  # 正数为多头，负数为空头
    avg_cost: float               # 平均成本
    market_value: float = 0.0     # 市值
    unrealized_pnl: float = 0.0   # 未实现盈亏
    realized_pnl: float = 0.0     # 已实现盈亏

    @property
    def is_long(self) -> bool:
        return self.quantity > 0

    @property
    def is_short(self) -> bool:
        return self.quantity < 0

    @property
    def is_flat(self) -> bool:
        return self.quantity == 0


class FutuTradeExecutor:
    """
    富途交易执行器
    实现高频交易核心功能
    """

    def __init__(
        self,
        pool: Optional[OpenDConnectionPool] = None,
        trd_env: int = 1,  # 0=真实, 1=模拟
        market: str = "US",
        max_slippage: float = 0.002,  # 最大允许滑点 0.2%
        order_timeout: float = 5.0,
        enable_short: bool = True
    ):
        self.pool = pool or get_default_pool()
        self.trd_env = trd_env
        self.market = market
        self.max_slippage = max_slippage
        self.order_timeout = order_timeout
        self.enable_short = enable_short

        # 执行指标
        self._order_count = 0
        self._successful_orders = 0
        self._total_slippage = 0.0
        self._total_latency = 0.0
        self._executor = ThreadPoolExecutor(max_workers=4)
        self._positions: Dict[str, Position] = {}
        self._lock = threading.Lock()

        # 订单回调
        self._order_callbacks: List[Callable[[OrderResult], None]] = []

    def register_order_callback(self, callback: Callable[[OrderResult], None]):
        """注册订单回调"""
        self._order_callbacks.append(callback)

    def _notify_order_result(self, result: OrderResult):
        """通知订单结果"""
        for callback in self._order_callbacks:
            try:
                callback(result)
            except Exception as e:
                logger.error(f"Order callback error: {e}")

    def _to_futu_symbol(self, symbol: str) -> str:
        """转换为富途格式股票代码"""
        if "." in symbol:
            return symbol
        return f"US.{symbol}"

    def _get_trd_side(self, side: OrderSide, current_position: int = 0) -> str:
        """获取交易方向"""
        if side == OrderSide.LONG:
            return TrdSide.BUY if FUTU_AVAILABLE else "BUY"
        elif side == OrderSide.SHORT:
            return TrdSide.SELL_SHORT if FUTU_AVAILABLE else "SELL_SHORT"
        elif side == OrderSide.FLAT:
            if current_position > 0:
                return TrdSide.SELL if FUTU_AVAILABLE else "SELL"
            else:
                return TrdSide.BUY_BACK if FUTU_AVAILABLE else "BUY_BACK"
        return TrdSide.BUY if FUTU_AVAILABLE else "BUY"

    def _get_order_type(self, order_type: OrderType) -> Any:
        """转换订单类型"""
        if not FUTU_AVAILABLE:
            return order_type.value

        mapping = {
            OrderType.MARKET: FutuOrderType.MARKET,
            OrderType.LIMIT: getattr(FutuOrderType, 'NORMAL', FutuOrderType.LIMIT),
        }
        return mapping.get(order_type, FutuOrderType.MARKET)

    async def get_current_price(self, symbol: str) -> Optional[float]:
        """获取当前价格"""
        futu_symbol = self._to_futu_symbol(symbol)

        if not FUTU_AVAILABLE:
            # Mock price for testing
            import random
            base_prices = {"TQQQ": 75.0, "QQQ": 490.0, "SOXL": 30.0, "SPXL": 180.0}
            base = base_prices.get(symbol, 100.0)
            return base * (1 + random.uniform(-0.001, 0.001))

        try:
            with self.pool.get_connection() as client:
                ret, data = client.quote_ctx.get_market_snapshot([futu_symbol])
                if ret == RET_OK and len(data) > 0:
                    return float(data.iloc[0]['last_price'])
        except Exception as e:
            logger.error(f"Failed to get price for {symbol}: {e}")
        return None

    async def get_position(self, symbol: str) -> Optional[Position]:
        """获取持仓"""
        futu_symbol = self._to_futu_symbol(symbol)

        with self._lock:
            if symbol in self._positions:
                return self._positions[symbol]

        if not FUTU_AVAILABLE:
            return Position(symbol=symbol, quantity=0, avg_cost=0.0)

        try:
            with self.pool.get_connection() as client:
                trd_env = TrdEnv.REAL if self.trd_env == 0 else TrdEnv.SIMULATE
                ret, data = client.trade_ctx.position_list_query(
                    code=futu_symbol,
                    trd_env=trd_env
                )
                if ret == RET_OK and len(data) > 0:
                    row = data.iloc[0]
                    position = Position(
                        symbol=symbol,
                        quantity=int(row['qty']),
                        avg_cost=float(row['cost_price']),
                        market_value=float(row.get('market_val', 0)),
                        unrealized_pnl=float(row.get('pl_val', 0))
                    )
                    with self._lock:
                        self._positions[symbol] = position
                    return position
        except Exception as e:
            logger.error(f"Failed to get position for {symbol}: {e}")

        return Position(symbol=symbol, quantity=0, avg_cost=0.0)

    async def long(
        self,
        symbol: str,
        quantity: int,
        order_type: OrderType = OrderType.MARKET,
        price: Optional[float] = None
    ) -> OrderResult:
        """
        做多（买入开仓）

        Args:
            symbol: 股票代码
            quantity: 买入数量
            order_type: 订单类型
            price: 限价（限价单时必填）

        Returns:
            OrderResult: 订单结果
        """
        request = OrderRequest(
            symbol=symbol,
            side=OrderSide.LONG,
            quantity=quantity,
            order_type=order_type,
            price=price
        )
        return await self._execute_order(request)

    async def short(
        self,
        symbol: str,
        quantity: int,
        order_type: OrderType = OrderType.MARKET,
        price: Optional[float] = None
    ) -> OrderResult:
        """
        做空（卖空开仓）

        Args:
            symbol: 股票代码
            quantity: 卖空数量
            order_type: 订单类型
            price: 限价（限价单时必填）

        Returns:
            OrderResult: 订单结果
        """
        if not self.enable_short:
            return OrderResult(
                success=False,
                symbol=symbol,
                side=OrderSide.SHORT,
                quantity=quantity,
                state=OrderState.REJECTED,
                error_message="Short selling is disabled"
            )

        request = OrderRequest(
            symbol=symbol,
            side=OrderSide.SHORT,
            quantity=quantity,
            order_type=order_type,
            price=price
        )
        return await self._execute_order(request)

    async def flat(
        self,
        symbol: str,
        quantity: Optional[int] = None
    ) -> OrderResult:
        """
        平仓

        Args:
            symbol: 股票代码
            quantity: 平仓数量（None表示全部平仓）

        Returns:
            OrderResult: 订单结果
        """
        position = await self.get_position(symbol)

        if position is None or position.is_flat:
            return OrderResult(
                success=True,
                symbol=symbol,
                side=OrderSide.FLAT,
                quantity=0,
                state=OrderState.FILLED,
                error_message="No position to close"
            )

        close_qty = quantity or abs(position.quantity)
        close_qty = min(close_qty, abs(position.quantity))

        request = OrderRequest(
            symbol=symbol,
            side=OrderSide.FLAT,
            quantity=close_qty,
            order_type=OrderType.MARKET
        )

        return await self._execute_order(request, current_position=position.quantity)

    async def _execute_order(
        self,
        request: OrderRequest,
        current_position: int = 0
    ) -> OrderResult:
        """执行订单"""
        start_time = time.perf_counter()
        self._order_count += 1

        futu_symbol = self._to_futu_symbol(request.symbol)
        trd_side = self._get_trd_side(request.side, current_position)
        order_type = self._get_order_type(request.order_type)

        # 获取当前价格用于计算滑点
        current_price = await self.get_current_price(request.symbol)

        result = OrderResult(
            success=False,
            client_order_id=request.client_order_id,
            symbol=request.symbol,
            side=request.side,
            quantity=request.quantity,
            price=request.price or current_price or 0.0,
            state=OrderState.PENDING
        )

        if not FUTU_AVAILABLE:
            # Mock execution for testing
            await asyncio.sleep(0.001)  # Simulate network latency
            result.success = True
            result.order_id = f"MOCK_{request.client_order_id}"
            result.filled_quantity = request.quantity
            result.filled_price = current_price * (1 + 0.0001) if current_price else 0.0
            result.state = OrderState.FILLED
            result.latency_ms = (time.perf_counter() - start_time) * 1000

            if current_price and result.filled_price:
                result.slippage = abs(result.filled_price - current_price) / current_price

            self._successful_orders += 1
            self._total_latency += result.latency_ms
            self._total_slippage += result.slippage

            logger.info(f"[MOCK] Order executed: {result.to_dict()}")
            self._notify_order_result(result)
            return result

        try:
            with self.pool.get_connection() as client:
                trd_env = TrdEnv.REAL if self.trd_env == 0 else TrdEnv.SIMULATE

                # 下单
                ret, data = client.trade_ctx.place_order(
                    price=request.price or 0,
                    qty=request.quantity,
                    code=futu_symbol,
                    trd_side=trd_side,
                    order_type=order_type,
                    trd_env=trd_env
                )

                result.latency_ms = (time.perf_counter() - start_time) * 1000

                if ret == RET_OK:
                    order_id = str(data.iloc[0]['order_id'])
                    result.order_id = order_id
                    result.state = OrderState.SUBMITTED

                    # 等待成交确认
                    fill_result = await self._wait_for_fill(
                        client, order_id, trd_env
                    )

                    if fill_result:
                        result.success = True
                        result.state = OrderState.FILLED
                        result.filled_quantity = fill_result.get('dealt_qty', request.quantity)
                        result.filled_price = fill_result.get('dealt_avg_price', request.price or 0)

                        # 计算滑点
                        if current_price and result.filled_price:
                            result.slippage = abs(result.filled_price - current_price) / current_price

                            if result.slippage > self.max_slippage:
                                logger.warning(
                                    f"Slippage exceeded: {result.slippage:.4%} > {self.max_slippage:.4%}"
                                )

                        self._successful_orders += 1
                        self._total_slippage += result.slippage
                    else:
                        result.state = OrderState.FAILED
                        result.error_message = "Order fill timeout"
                else:
                    result.state = OrderState.REJECTED
                    result.error_message = str(data)

                self._total_latency += result.latency_ms

        except Exception as e:
            result.state = OrderState.FAILED
            result.error_message = str(e)
            result.latency_ms = (time.perf_counter() - start_time) * 1000
            logger.error(f"Order execution failed: {e}")

        self._notify_order_result(result)
        logger.info(f"Order executed: {result.to_dict()}")
        return result

    async def _wait_for_fill(
        self,
        client: OpenDClient,
        order_id: str,
        trd_env: Any,
        timeout: float = None
    ) -> Optional[Dict]:
        """等待订单成交"""
        timeout = timeout or self.order_timeout
        start = time.time()

        while time.time() - start < timeout:
            try:
                ret, data = client.trade_ctx.order_list_query(
                    order_id=order_id,
                    trd_env=trd_env
                )

                if ret == RET_OK and len(data) > 0:
                    order = data.iloc[0]
                    status = order['order_status']

                    if status in [OrderStatus.FILLED_ALL, 'FILLED_ALL']:
                        return {
                            'dealt_qty': int(order['dealt_qty']),
                            'dealt_avg_price': float(order['dealt_avg_price'])
                        }
                    elif status in [OrderStatus.CANCELLED_ALL, OrderStatus.FAILED,
                                   'CANCELLED_ALL', 'FAILED']:
                        return None

            except Exception as e:
                logger.warning(f"Error checking order status: {e}")

            await asyncio.sleep(0.05)  # 50ms polling interval

        return None

    def get_execution_metrics(self) -> Dict[str, Any]:
        """获取执行指标"""
        return {
            "total_orders": self._order_count,
            "successful_orders": self._successful_orders,
            "success_rate": self._successful_orders / max(1, self._order_count),
            "average_slippage": self._total_slippage / max(1, self._successful_orders),
            "average_latency_ms": self._total_latency / max(1, self._order_count)
        }

    async def close(self):
        """关闭执行器"""
        self._executor.shutdown(wait=False)


# 便捷函数
async def quick_long(symbol: str, quantity: int, **kwargs) -> OrderResult:
    """快速做多"""
    executor = FutuTradeExecutor()
    return await executor.long(symbol, quantity, **kwargs)


async def quick_short(symbol: str, quantity: int, **kwargs) -> OrderResult:
    """快速做空"""
    executor = FutuTradeExecutor()
    return await executor.short(symbol, quantity, **kwargs)


async def quick_flat(symbol: str, quantity: Optional[int] = None) -> OrderResult:
    """快速平仓"""
    executor = FutuTradeExecutor()
    return await executor.flat(symbol, quantity)
