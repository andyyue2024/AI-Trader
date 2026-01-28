# -*- coding: utf-8 -*-
"""
技术分析策略库
包含多种经典技术分析策略
"""

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from .strategy_marketplace import BaseStrategy, StrategyRegistry


@dataclass
class TechnicalIndicators:
    """技术指标数据"""
    symbol: str
    price: float
    volume: float = 0.0

    # 移动平均
    sma_5: float = 0.0
    sma_10: float = 0.0
    sma_20: float = 0.0
    sma_50: float = 0.0
    sma_200: float = 0.0
    ema_12: float = 0.0
    ema_26: float = 0.0

    # MACD
    macd: float = 0.0
    macd_signal: float = 0.0
    macd_hist: float = 0.0

    # RSI
    rsi_14: float = 50.0

    # Bollinger Bands
    bb_upper: float = 0.0
    bb_middle: float = 0.0
    bb_lower: float = 0.0

    # ATR
    atr_14: float = 0.0

    # Volume
    volume_sma_20: float = 0.0

    # Price levels
    high_20: float = 0.0
    low_20: float = 0.0
    high_52w: float = 0.0
    low_52w: float = 0.0


class TechnicalAnalyzer:
    """技术指标计算器"""

    @staticmethod
    def calculate_sma(prices: List[float], period: int) -> float:
        """计算简单移动平均"""
        if len(prices) < period:
            return prices[-1] if prices else 0.0
        return sum(prices[-period:]) / period

    @staticmethod
    def calculate_ema(prices: List[float], period: int) -> float:
        """计算指数移动平均"""
        if len(prices) < period:
            return prices[-1] if prices else 0.0

        multiplier = 2 / (period + 1)
        ema = prices[0]
        for price in prices[1:]:
            ema = (price - ema) * multiplier + ema
        return ema

    @staticmethod
    def calculate_rsi(prices: List[float], period: int = 14) -> float:
        """计算相对强弱指数"""
        if len(prices) < period + 1:
            return 50.0

        gains = []
        losses = []

        for i in range(1, len(prices)):
            change = prices[i] - prices[i-1]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))

        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period

        if avg_loss == 0:
            return 100.0

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    @staticmethod
    def calculate_macd(prices: List[float]) -> Tuple[float, float, float]:
        """计算 MACD"""
        if len(prices) < 26:
            return 0.0, 0.0, 0.0

        ema_12 = TechnicalAnalyzer.calculate_ema(prices, 12)
        ema_26 = TechnicalAnalyzer.calculate_ema(prices, 26)
        macd = ema_12 - ema_26

        # 简化：使用 MACD 的 9 日 EMA 作为信号线
        signal = macd * 0.9  # 简化计算
        histogram = macd - signal

        return macd, signal, histogram

    @staticmethod
    def calculate_bollinger_bands(prices: List[float], period: int = 20, std_dev: float = 2.0) -> Tuple[float, float, float]:
        """计算布林带"""
        if len(prices) < period:
            price = prices[-1] if prices else 0.0
            return price, price, price

        sma = sum(prices[-period:]) / period
        variance = sum((p - sma) ** 2 for p in prices[-period:]) / period
        std = math.sqrt(variance)

        upper = sma + std_dev * std
        lower = sma - std_dev * std

        return upper, sma, lower

    @staticmethod
    def calculate_atr(highs: List[float], lows: List[float], closes: List[float], period: int = 14) -> float:
        """计算平均真实波幅"""
        if len(closes) < period + 1:
            return 0.0

        tr_values = []
        for i in range(1, len(closes)):
            high_low = highs[i] - lows[i]
            high_close = abs(highs[i] - closes[i-1])
            low_close = abs(lows[i] - closes[i-1])
            tr = max(high_low, high_close, low_close)
            tr_values.append(tr)

        return sum(tr_values[-period:]) / period


# ============ 技术分析策略 ============

@StrategyRegistry.register
class RSIStrategy(BaseStrategy):
    """RSI 策略"""

    def __init__(self, oversold: float = 30, overbought: float = 70):
        super().__init__("RSI Strategy", "1.0.0")
        self.author = "AI-Trader"
        self.description = "RSI-based mean reversion strategy. Buy when oversold, sell when overbought."
        self.tags = ["rsi", "mean-reversion", "oscillator"]
        self.oversold = oversold
        self.overbought = overbought

    def generate_signal(self, market_data: Dict, positions: Dict) -> Dict[str, str]:
        signals = {}

        for symbol, data in market_data.items():
            rsi = data.get("rsi_14", 50)

            if rsi < self.oversold:
                signals[symbol] = "long"
            elif rsi > self.overbought:
                if symbol in positions:
                    signals[symbol] = "flat"
                else:
                    signals[symbol] = "short"
            else:
                signals[symbol] = "hold"

        return signals


@StrategyRegistry.register
class MACDStrategy(BaseStrategy):
    """MACD 策略"""

    def __init__(self):
        super().__init__("MACD Crossover Strategy", "1.0.0")
        self.author = "AI-Trader"
        self.description = "MACD crossover strategy. Buy on bullish crossover, sell on bearish crossover."
        self.tags = ["macd", "trend-following", "crossover"]
        self.prev_histogram: Dict[str, float] = {}

    def generate_signal(self, market_data: Dict, positions: Dict) -> Dict[str, str]:
        signals = {}

        for symbol, data in market_data.items():
            hist = data.get("macd_hist", 0)
            prev_hist = self.prev_histogram.get(symbol, 0)

            # 检测交叉
            if prev_hist <= 0 < hist:  # 金叉
                signals[symbol] = "long"
            elif prev_hist >= 0 > hist:  # 死叉
                if symbol in positions:
                    signals[symbol] = "flat"
                else:
                    signals[symbol] = "short"
            else:
                signals[symbol] = "hold"

            self.prev_histogram[symbol] = hist

        return signals


@StrategyRegistry.register
class BollingerBandsStrategy(BaseStrategy):
    """布林带策略"""

    def __init__(self):
        super().__init__("Bollinger Bands Strategy", "1.0.0")
        self.author = "AI-Trader"
        self.description = "Bollinger Bands mean reversion. Buy at lower band, sell at upper band."
        self.tags = ["bollinger", "mean-reversion", "volatility"]

    def generate_signal(self, market_data: Dict, positions: Dict) -> Dict[str, str]:
        signals = {}

        for symbol, data in market_data.items():
            price = data.get("price", 0)
            bb_upper = data.get("bb_upper", price)
            bb_lower = data.get("bb_lower", price)
            bb_middle = data.get("bb_middle", price)

            if price <= bb_lower:  # 触及下轨
                signals[symbol] = "long"
            elif price >= bb_upper:  # 触及上轨
                if symbol in positions:
                    signals[symbol] = "flat"
                else:
                    signals[symbol] = "hold"
            elif symbol in positions and price >= bb_middle:
                # 有持仓且价格回到中轨，考虑止盈
                signals[symbol] = "hold"
            else:
                signals[symbol] = "hold"

        return signals


@StrategyRegistry.register
class GoldenCrossStrategy(BaseStrategy):
    """金叉/死叉策略"""

    def __init__(self, fast_period: int = 50, slow_period: int = 200):
        super().__init__("Golden Cross Strategy", "1.0.0")
        self.author = "AI-Trader"
        self.description = f"SMA {fast_period}/{slow_period} crossover strategy. Classic trend following."
        self.tags = ["moving-average", "trend-following", "crossover"]
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.prev_fast: Dict[str, float] = {}
        self.prev_slow: Dict[str, float] = {}

    def generate_signal(self, market_data: Dict, positions: Dict) -> Dict[str, str]:
        signals = {}

        for symbol, data in market_data.items():
            fast_ma = data.get(f"sma_{self.fast_period}", 0) or data.get("sma_50", 0)
            slow_ma = data.get(f"sma_{self.slow_period}", 0) or data.get("sma_200", 0)

            prev_fast = self.prev_fast.get(symbol, fast_ma)
            prev_slow = self.prev_slow.get(symbol, slow_ma)

            # 金叉：快线从下穿越慢线
            if prev_fast <= prev_slow and fast_ma > slow_ma:
                signals[symbol] = "long"
            # 死叉：快线从上穿越慢线
            elif prev_fast >= prev_slow and fast_ma < slow_ma:
                if symbol in positions:
                    signals[symbol] = "flat"
                else:
                    signals[symbol] = "short"
            else:
                signals[symbol] = "hold"

            self.prev_fast[symbol] = fast_ma
            self.prev_slow[symbol] = slow_ma

        return signals


@StrategyRegistry.register
class TurtleStrategy(BaseStrategy):
    """海龟交易策略"""

    def __init__(self, entry_period: int = 20, exit_period: int = 10):
        super().__init__("Turtle Trading Strategy", "1.0.0")
        self.author = "AI-Trader"
        self.description = f"Classic Turtle Trading: {entry_period}-day breakout entry, {exit_period}-day breakout exit."
        self.tags = ["turtle", "breakout", "trend-following", "classic"]
        self.entry_period = entry_period
        self.exit_period = exit_period

    def generate_signal(self, market_data: Dict, positions: Dict) -> Dict[str, str]:
        signals = {}

        for symbol, data in market_data.items():
            price = data.get("price", 0)
            high_n = data.get(f"high_{self.entry_period}", price)
            low_n = data.get(f"low_{self.entry_period}", price)
            high_exit = data.get(f"high_{self.exit_period}", price)
            low_exit = data.get(f"low_{self.exit_period}", price)

            if symbol not in positions:
                # 无持仓：突破 N 日高点做多
                if price >= high_n:
                    signals[symbol] = "long"
                elif price <= low_n:
                    signals[symbol] = "short"
                else:
                    signals[symbol] = "hold"
            else:
                # 有持仓：跌破 N/2 日低点平仓
                pos = positions[symbol]
                if hasattr(pos, 'side'):
                    if pos.side == "long" and price <= low_exit:
                        signals[symbol] = "flat"
                    elif pos.side == "short" and price >= high_exit:
                        signals[symbol] = "flat"
                    else:
                        signals[symbol] = "hold"
                else:
                    signals[symbol] = "hold"

        return signals


@StrategyRegistry.register
class VolumeBreakoutStrategy(BaseStrategy):
    """成交量突破策略"""

    def __init__(self, volume_multiplier: float = 2.0):
        super().__init__("Volume Breakout Strategy", "1.0.0")
        self.author = "AI-Trader"
        self.description = f"Enter on volume spike ({volume_multiplier}x average) with price breakout."
        self.tags = ["volume", "breakout", "momentum"]
        self.volume_multiplier = volume_multiplier

    def generate_signal(self, market_data: Dict, positions: Dict) -> Dict[str, str]:
        signals = {}

        for symbol, data in market_data.items():
            price = data.get("price", 0)
            volume = data.get("volume", 0)
            avg_volume = data.get("volume_sma_20", volume)
            high_20 = data.get("high_20", price)
            low_20 = data.get("low_20", price)

            # 成交量突破
            volume_spike = volume >= avg_volume * self.volume_multiplier if avg_volume > 0 else False

            if volume_spike:
                if price >= high_20:  # 放量突破高点
                    signals[symbol] = "long"
                elif price <= low_20:  # 放量跌破低点
                    if symbol in positions:
                        signals[symbol] = "flat"
                    else:
                        signals[symbol] = "short"
                else:
                    signals[symbol] = "hold"
            else:
                signals[symbol] = "hold"

        return signals


# ============ 策略组合器 ============

class StrategyEnsemble:
    """策略组合器：结合多个策略的信号"""

    def __init__(self, strategies: List[BaseStrategy], weights: List[float] = None):
        self.strategies = strategies
        self.weights = weights or [1.0] * len(strategies)

        # 归一化权重
        total = sum(self.weights)
        self.weights = [w / total for w in self.weights]

    def generate_signal(self, market_data: Dict, positions: Dict) -> Dict[str, str]:
        """生成综合信号"""
        signal_scores: Dict[str, Dict[str, float]] = {}

        # 收集所有策略的信号
        for strategy, weight in zip(self.strategies, self.weights):
            signals = strategy.generate_signal(market_data, positions)

            for symbol, signal in signals.items():
                if symbol not in signal_scores:
                    signal_scores[symbol] = {"long": 0, "short": 0, "flat": 0, "hold": 0}

                signal_scores[symbol][signal] += weight

        # 选择得分最高的信号
        final_signals = {}
        for symbol, scores in signal_scores.items():
            best_signal = max(scores, key=scores.get)

            # 如果 hold 分数最高但其他信号也有一定分数，可能需要特殊处理
            if best_signal == "hold" and scores["long"] > 0.3:
                best_signal = "long"
            elif best_signal == "hold" and scores["short"] > 0.3:
                best_signal = "short"

            final_signals[symbol] = best_signal

        return final_signals


if __name__ == "__main__":
    # 测试技术分析策略
    print("=== Technical Analysis Strategies ===")

    # 模拟市场数据
    market_data = {
        "TQQQ": {
            "price": 50.0,
            "rsi_14": 25,  # 超卖
            "macd_hist": 0.5,
            "bb_lower": 48.0,
            "bb_upper": 55.0,
            "bb_middle": 51.5,
            "sma_50": 49.0,
            "sma_200": 48.0,
            "high_20": 52.0,
            "low_20": 47.0,
            "volume": 1000000,
            "volume_sma_20": 500000
        }
    }

    positions = {}

    # 测试各策略
    strategies = [
        RSIStrategy(),
        MACDStrategy(),
        BollingerBandsStrategy(),
        GoldenCrossStrategy(),
        TurtleStrategy(),
        VolumeBreakoutStrategy()
    ]

    for strategy in strategies:
        signals = strategy.generate_signal(market_data, positions)
        print(f"{strategy.name}: {signals}")

    # 测试策略组合
    print("\n=== Strategy Ensemble ===")
    ensemble = StrategyEnsemble(strategies[:3], [0.4, 0.3, 0.3])
    combined = ensemble.generate_signal(market_data, positions)
    print(f"Combined Signal: {combined}")
