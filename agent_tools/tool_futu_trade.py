# -*- coding: utf-8 -*-
"""
富途交易 MCP 工具
基于 FastMCP 提供交易操作接口，支持 long/short/flat
"""

import asyncio
import json
import logging
import os
import sys
import time
from typing import Any, Dict, List, Optional

from fastmcp import FastMCP

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from tools.general_tools import get_config_value, write_config_value

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建 MCP 服务
mcp = FastMCP("FutuTradeTools")

# 懒加载富途模块
_futu_executor = None
_quote_subscriber = None
_risk_manager = None


def _get_executor():
    """获取交易执行器（懒加载）"""
    global _futu_executor
    if _futu_executor is None:
        from futu.trade_executor import FutuTradeExecutor
        from futu.opend_client import init_opend, OpenDConfig

        # 初始化 OpenD 连接
        config = OpenDConfig(
            host=os.getenv("OPEND_HOST", "127.0.0.1"),
            port=int(os.getenv("OPEND_PORT", "11111")),
            trd_env=int(os.getenv("OPEND_TRD_ENV", "1")),  # 默认模拟
            password=os.getenv("OPEND_TRADE_PASSWORD")
        )
        init_opend(config)

        _futu_executor = FutuTradeExecutor(
            trd_env=config.trd_env,
            max_slippage=0.002,  # 0.2%
            enable_short=True
        )
    return _futu_executor


def _get_quote_subscriber():
    """获取行情订阅器（懒加载）"""
    global _quote_subscriber
    if _quote_subscriber is None:
        from futu.quote_subscriber import FutuQuoteSubscriber
        _quote_subscriber = FutuQuoteSubscriber()
    return _quote_subscriber


def _get_risk_manager():
    """获取风险管理器（懒加载）"""
    global _risk_manager
    if _risk_manager is None:
        from risk_control.risk_manager import RiskManager, RiskConfig
        _risk_manager = RiskManager(RiskConfig(
            daily_loss_threshold=0.03,     # 3% 日内熔断
            max_drawdown=0.15,              # 15% 最大回撤
            max_slippage=0.002              # 0.2% 滑点
        ))
        # 初始化权益
        initial_cash = get_config_value("INITIAL_CASH", 10000.0)
        _risk_manager.initialize(initial_cash)
    return _risk_manager


@mcp.tool()
async def long(symbol: str, quantity: int, price: Optional[float] = None) -> Dict[str, Any]:
    """
    做多（买入开仓）

    开仓买入指定数量的股票，支持市价单和限价单。
    系统会自动进行风控检查，确保滑点≤0.2%，并在日内亏损超过3%时触发熔断。

    Args:
        symbol: 股票代码，如 "TQQQ", "QQQ", "AAPL" 等
        quantity: 买入数量（股数）
        price: 限价（可选，不填则使用市价单）

    Returns:
        Dict[str, Any]:
          - success: 是否成功
          - order_id: 订单ID
          - filled_price: 成交价格
          - slippage: 滑点百分比
          - latency_ms: 延迟(毫秒)
          - error: 错误信息（如有）

    Example:
        >>> result = await long("TQQQ", 100)
        >>> print(result)  # {"success": true, "order_id": "xxx", "filled_price": 75.50, ...}
    """
    executor = _get_executor()
    risk_manager = _get_risk_manager()
    subscriber = _get_quote_subscriber()

    # 获取当前价格
    quote = await subscriber.get_quote(symbol)
    current_price = quote.last_price if quote else (price or 0)

    # 风控检查
    risk_check = risk_manager.pre_trade_check(
        symbol=symbol,
        side="long",
        quantity=quantity,
        price=current_price
    )

    if not risk_check.allowed:
        logger.warning(f"Trade rejected by risk control: {risk_check.reasons}")
        return {
            "success": False,
            "error": f"Risk control rejected: {', '.join(risk_check.reasons)}",
            "risk_level": risk_check.risk_level.value,
            "warnings": risk_check.warnings
        }

    # 记录开始时间
    start_time = time.perf_counter()

    try:
        # 执行交易
        from futu.trade_executor import OrderType
        order_type = OrderType.LIMIT if price else OrderType.MARKET
        result = await executor.long(symbol, quantity, order_type=order_type, price=price)

        # 交易后检查
        if result.success:
            risk_manager.post_trade_check(
                symbol=symbol,
                expected_price=current_price,
                executed_price=result.filled_price,
                order_id=result.order_id
            )

            # 标记已交易
            write_config_value("IF_TRADE", True)

        return result.to_dict()

    except Exception as e:
        logger.error(f"Long order failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "latency_ms": (time.perf_counter() - start_time) * 1000
        }


@mcp.tool()
async def short(symbol: str, quantity: int, price: Optional[float] = None) -> Dict[str, Any]:
    """
    做空（卖空开仓）

    卖空指定数量的股票，支持市价单和限价单。
    系统会自动进行风控检查，确保滑点≤0.2%，并在日内亏损超过3%时触发熔断。

    Args:
        symbol: 股票代码，如 "TQQQ", "QQQ", "AAPL" 等
        quantity: 卖空数量（股数）
        price: 限价（可选，不填则使用市价单）

    Returns:
        Dict[str, Any]:
          - success: 是否成功
          - order_id: 订单ID
          - filled_price: 成交价格
          - slippage: 滑点百分比
          - latency_ms: 延迟(毫秒)
          - error: 错误信息（如有）

    Example:
        >>> result = await short("TQQQ", 100)
        >>> print(result)  # {"success": true, "order_id": "xxx", ...}
    """
    executor = _get_executor()
    risk_manager = _get_risk_manager()
    subscriber = _get_quote_subscriber()

    # 获取当前价格
    quote = await subscriber.get_quote(symbol)
    current_price = quote.last_price if quote else (price or 0)

    # 风控检查
    risk_check = risk_manager.pre_trade_check(
        symbol=symbol,
        side="short",
        quantity=quantity,
        price=current_price
    )

    if not risk_check.allowed:
        logger.warning(f"Short order rejected by risk control: {risk_check.reasons}")
        return {
            "success": False,
            "error": f"Risk control rejected: {', '.join(risk_check.reasons)}",
            "risk_level": risk_check.risk_level.value,
            "warnings": risk_check.warnings
        }

    start_time = time.perf_counter()

    try:
        from futu.trade_executor import OrderType
        order_type = OrderType.LIMIT if price else OrderType.MARKET
        result = await executor.short(symbol, quantity, order_type=order_type, price=price)

        if result.success:
            risk_manager.post_trade_check(
                symbol=symbol,
                expected_price=current_price,
                executed_price=result.filled_price,
                order_id=result.order_id
            )
            write_config_value("IF_TRADE", True)

        return result.to_dict()

    except Exception as e:
        logger.error(f"Short order failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "latency_ms": (time.perf_counter() - start_time) * 1000
        }


@mcp.tool()
async def flat(symbol: str, quantity: Optional[int] = None) -> Dict[str, Any]:
    """
    平仓

    平掉指定股票的持仓。如果不指定数量，则全部平仓。

    Args:
        symbol: 股票代码
        quantity: 平仓数量（可选，不填则全部平仓）

    Returns:
        Dict[str, Any]:
          - success: 是否成功
          - order_id: 订单ID
          - filled_price: 成交价格
          - closed_quantity: 平仓数量
          - error: 错误信息（如有）

    Example:
        >>> result = await flat("TQQQ")  # 全部平仓
        >>> result = await flat("TQQQ", 50)  # 平仓50股
    """
    executor = _get_executor()

    start_time = time.perf_counter()

    try:
        result = await executor.flat(symbol, quantity)

        if result.success:
            write_config_value("IF_TRADE", True)

        return result.to_dict()

    except Exception as e:
        logger.error(f"Flat order failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "latency_ms": (time.perf_counter() - start_time) * 1000
        }


@mcp.tool()
async def get_realtime_quote(symbol: str) -> Dict[str, Any]:
    """
    获取实时行情

    获取指定股票的实时行情数据，包括最新价、买卖价、成交量等。

    Args:
        symbol: 股票代码

    Returns:
        Dict[str, Any]:
          - symbol: 股票代码
          - last_price: 最新价
          - bid_price: 买一价
          - ask_price: 卖一价
          - volume: 成交量
          - session: 交易时段 (pre_market/regular/after_hours)
    """
    subscriber = _get_quote_subscriber()

    try:
        quote = await subscriber.get_quote(symbol)
        if quote:
            return quote.to_dict()
        else:
            return {"error": f"No quote available for {symbol}"}
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
async def get_klines(symbol: str, period: str = "1m", count: int = 100) -> Dict[str, Any]:
    """
    获取K线数据

    获取指定股票的K线历史数据。

    Args:
        symbol: 股票代码
        period: K线周期，支持 "1m", "5m", "15m", "60m", "day"
        count: 获取数量

    Returns:
        Dict[str, Any]:
          - symbol: 股票代码
          - klines: K线数据列表
    """
    subscriber = _get_quote_subscriber()

    # 转换周期格式
    period_map = {
        "1m": "K_1M",
        "5m": "K_5M",
        "15m": "K_15M",
        "60m": "K_60M",
        "day": "K_DAY"
    }
    kl_type = period_map.get(period, "K_1M")

    try:
        klines = await subscriber.get_klines(symbol, kl_type, count)
        return {
            "symbol": symbol,
            "period": period,
            "count": len(klines),
            "klines": [k.to_dict() for k in klines]
        }
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
async def get_position(symbol: str) -> Dict[str, Any]:
    """
    获取持仓信息

    获取指定股票的当前持仓情况。

    Args:
        symbol: 股票代码

    Returns:
        Dict[str, Any]:
          - symbol: 股票代码
          - quantity: 持仓数量（正数多头，负数空头）
          - avg_cost: 平均成本
          - market_value: 市值
          - unrealized_pnl: 未实现盈亏
    """
    executor = _get_executor()

    try:
        position = await executor.get_position(symbol)
        if position:
            return {
                "symbol": position.symbol,
                "quantity": position.quantity,
                "avg_cost": position.avg_cost,
                "market_value": position.market_value,
                "unrealized_pnl": position.unrealized_pnl,
                "is_long": position.is_long,
                "is_short": position.is_short,
                "is_flat": position.is_flat
            }
        else:
            return {"error": f"No position for {symbol}"}
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def get_risk_status() -> Dict[str, Any]:
    """
    获取风控状态

    获取当前的风险控制状态，包括熔断器状态、回撤、滑点等。

    Returns:
        Dict[str, Any]:
          - risk_level: 风险级别 (low/medium/high/critical/halted)
          - can_trade: 是否允许交易
          - circuit_breaker: 熔断器状态
          - drawdown: 回撤监控状态
          - slippage: 滑点检查状态
    """
    risk_manager = _get_risk_manager()
    return risk_manager.get_status()


@mcp.tool()
def halt_trading(reason: str = "Manual halt") -> Dict[str, Any]:
    """
    停止交易

    手动触发熔断，停止所有交易操作。

    Args:
        reason: 停止原因

    Returns:
        Dict: 操作结果
    """
    risk_manager = _get_risk_manager()
    risk_manager.force_halt(reason)
    return {
        "success": True,
        "message": f"Trading halted: {reason}",
        "status": risk_manager.get_status()
    }


@mcp.tool()
def resume_trading() -> Dict[str, Any]:
    """
    恢复交易

    解除熔断状态，恢复交易操作。

    Returns:
        Dict: 操作结果
    """
    risk_manager = _get_risk_manager()
    risk_manager.resume_trading()
    return {
        "success": True,
        "message": "Trading resumed",
        "status": risk_manager.get_status()
    }


@mcp.tool()
def get_execution_metrics() -> Dict[str, Any]:
    """
    获取执行指标

    获取交易执行的性能指标，包括成功率、平均延迟、平均滑点等。

    Returns:
        Dict[str, Any]:
          - total_orders: 总订单数
          - success_rate: 成功率
          - average_slippage: 平均滑点
          - average_latency_ms: 平均延迟(毫秒)
    """
    executor = _get_executor()
    return executor.get_execution_metrics()


# 主入口
if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("FUTU_TRADE_HTTP_PORT", "8010"))
    print(f"Starting Futu Trade MCP service on port {port}")

    mcp.run(transport="streamable-http", host="0.0.0.0", port=port)
