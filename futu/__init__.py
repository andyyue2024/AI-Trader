# -*- coding: utf-8 -*-
"""
Futu OpenD 交易模块
实现高频交易功能，支持 TQQQ/QQQ 等美股标的
支持股票和期权交易，盘前/盘后/夜盘无缝接力
"""

from .opend_client import OpenDClient, OpenDConnectionPool
from .trade_executor import FutuTradeExecutor, OrderType, OrderSide
from .quote_subscriber import FutuQuoteSubscriber
from .session_manager import SessionManager, MarketSession, MarketType, is_market_open, get_current_session
from .options_trader import OptionTrader, OptionContract, OptionType, OptionChain

__all__ = [
    # 连接管理
    'OpenDClient',
    'OpenDConnectionPool',
    # 交易执行
    'FutuTradeExecutor',
    'OrderType',
    'OrderSide',
    # 行情订阅
    'FutuQuoteSubscriber',
    # 时段管理
    'SessionManager',
    'MarketSession',
    'MarketType',
    'is_market_open',
    'get_current_session',
    # 期权交易
    'OptionTrader',
    'OptionContract',
    'OptionType',
    'OptionChain'
]
