# -*- coding: utf-8 -*-
"""
策略模块
"""

from .strategy_marketplace import (
    BaseStrategy, StrategyMeta, StrategyRegistry, StrategyMarketplace,
    MomentumStrategy, MeanReversionStrategy, BreakoutStrategy
)

from .technical_strategies import (
    TechnicalIndicators, TechnicalAnalyzer,
    RSIStrategy, MACDStrategy, BollingerBandsStrategy,
    GoldenCrossStrategy, TurtleStrategy, VolumeBreakoutStrategy,
    StrategyEnsemble
)

__all__ = [
    # Base
    'BaseStrategy',
    'StrategyMeta',
    'StrategyRegistry',
    'StrategyMarketplace',

    # Basic Strategies
    'MomentumStrategy',
    'MeanReversionStrategy',
    'BreakoutStrategy',

    # Technical Analysis
    'TechnicalIndicators',
    'TechnicalAnalyzer',
    'RSIStrategy',
    'MACDStrategy',
    'BollingerBandsStrategy',
    'GoldenCrossStrategy',
    'TurtleStrategy',
    'VolumeBreakoutStrategy',

    # Ensemble
    'StrategyEnsemble'
]
