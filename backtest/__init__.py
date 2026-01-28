# -*- coding: utf-8 -*-
"""
回测模块
"""

from .backtest_engine import (
    BacktestConfig, BacktestEngine, BacktestResult,
    Position, Trade, run_backtest, simple_momentum_strategy
)

from .advanced_replay import (
    ReplayConfig, MarketTick, MarketDataLoader,
    AdvancedReplayEngine, ReplayController, run_replay
)

from .smart_filter import (
    FilterConfig, FilterResult, DatePatternMatcher,
    SmartFilter, DataIntegrityChecker
)

__all__ = [
    # Backtest Engine
    'BacktestConfig',
    'BacktestEngine',
    'BacktestResult',
    'Position',
    'Trade',
    'run_backtest',
    'simple_momentum_strategy',

    # Advanced Replay
    'ReplayConfig',
    'MarketTick',
    'MarketDataLoader',
    'AdvancedReplayEngine',
    'ReplayController',
    'run_replay',

    # Smart Filter
    'FilterConfig',
    'FilterResult',
    'DatePatternMatcher',
    'SmartFilter',
    'DataIntegrityChecker'
]
