# -*- coding: utf-8 -*-
"""
回测模块
"""

from .backtest_engine import (
    BacktestConfig, BacktestEngine, BacktestResult,
    Position, Trade, run_backtest, simple_momentum_strategy
)

__all__ = [
    'BacktestConfig',
    'BacktestEngine',
    'BacktestResult',
    'Position',
    'Trade',
    'run_backtest',
    'simple_momentum_strategy'
]
