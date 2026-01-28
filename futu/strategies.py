# -*- coding: utf-8 -*-
"""
AI 交易策略模块
提供多种交易策略供高频交易系统使用
"""

import logging
import math
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class Signal:
    """交易信号"""
    action: str  # long/short/flat/hold
    quantity: int
    price: Optional[float] = None
    reason: str = ""
    confidence: float = 0.5
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action": self.action,
            "quantity": self.quantity,
            "price": self.price,
            "reason": self.reason,
            "confidence": round(self.confidence, 2),
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit
        }


class BaseStrategy(ABC):
    """策略基类"""

    def __init__(self, name: str = "BaseStrategy"):
        self.name = name
        self._initialized = False

    @abstractmethod
    def analyze(self, market_data: Dict[str, Any]) -> Signal:
        """分析市场数据，生成交易信号"""
        pass

    def initialize(self, config: Dict[str, Any] = None):
        """初始化策略"""
        self._initialized = True

    def on_trade(self, result: Dict[str, Any]):
        """交易回调"""
        pass


class MomentumStrategy(BaseStrategy):
    """
    动量策略
    基于短期价格动量生成交易信号
    """

    def __init__(
        self,
        lookback_period: int = 5,
        momentum_threshold: float = 0.005,
        position_size: int = 10
    ):
        super().__init__("MomentumStrategy")
        self.lookback_period = lookback_period
        self.momentum_threshold = momentum_threshold
        self.position_size = position_size

    def analyze(self, market_data: Dict[str, Any]) -> Signal:
        """分析动量"""
        klines = market_data.get("klines", [])

        if len(klines) < self.lookback_period:
            return Signal(action="hold", quantity=0, reason="Insufficient data")

        # 计算动量
        closes = [k["close"] for k in klines[-self.lookback_period:]]
        momentum = (closes[-1] - closes[0]) / closes[0]

        # 计算成交量变化
        volumes = [k.get("volume", 0) for k in klines[-self.lookback_period:]]
        avg_volume = sum(volumes) / len(volumes) if volumes else 0
        current_volume = volumes[-1] if volumes else 0
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1

        # 生成信号
        if momentum > self.momentum_threshold and volume_ratio > 1.2:
            return Signal(
                action="long",
                quantity=self.position_size,
                reason=f"Strong momentum: {momentum:.2%}, volume ratio: {volume_ratio:.1f}x",
                confidence=min(0.9, 0.5 + momentum * 10),
                stop_loss=closes[-1] * 0.98,
                take_profit=closes[-1] * 1.02
            )
        elif momentum < -self.momentum_threshold and volume_ratio > 1.2:
            return Signal(
                action="short",
                quantity=self.position_size,
                reason=f"Negative momentum: {momentum:.2%}, volume ratio: {volume_ratio:.1f}x",
                confidence=min(0.9, 0.5 + abs(momentum) * 10),
                stop_loss=closes[-1] * 1.02,
                take_profit=closes[-1] * 0.98
            )
        else:
            return Signal(
                action="hold",
                quantity=0,
                reason=f"Neutral: momentum={momentum:.2%}"
            )


class MeanReversionStrategy(BaseStrategy):
    """
    均值回归策略
    当价格偏离均线过远时反向操作
    """

    def __init__(
        self,
        ma_period: int = 20,
        std_multiplier: float = 2.0,
        position_size: int = 10
    ):
        super().__init__("MeanReversionStrategy")
        self.ma_period = ma_period
        self.std_multiplier = std_multiplier
        self.position_size = position_size

    def analyze(self, market_data: Dict[str, Any]) -> Signal:
        """分析均值回归"""
        klines = market_data.get("klines", [])

        if len(klines) < self.ma_period:
            return Signal(action="hold", quantity=0, reason="Insufficient data")

        closes = [k["close"] for k in klines[-self.ma_period:]]
        current_price = closes[-1]

        # 计算均值和标准差
        ma = sum(closes) / len(closes)
        variance = sum((c - ma) ** 2 for c in closes) / len(closes)
        std = math.sqrt(variance)

        # 计算 z-score
        z_score = (current_price - ma) / std if std > 0 else 0

        # 布林带
        upper_band = ma + self.std_multiplier * std
        lower_band = ma - self.std_multiplier * std

        if z_score < -self.std_multiplier:
            return Signal(
                action="long",
                quantity=self.position_size,
                reason=f"Oversold: z-score={z_score:.2f}, price below lower band",
                confidence=min(0.9, 0.5 + abs(z_score) * 0.15),
                stop_loss=lower_band * 0.98,
                take_profit=ma
            )
        elif z_score > self.std_multiplier:
            return Signal(
                action="short",
                quantity=self.position_size,
                reason=f"Overbought: z-score={z_score:.2f}, price above upper band",
                confidence=min(0.9, 0.5 + abs(z_score) * 0.15),
                stop_loss=upper_band * 1.02,
                take_profit=ma
            )
        else:
            return Signal(
                action="hold",
                quantity=0,
                reason=f"In range: z-score={z_score:.2f}"
            )


class RSIStrategy(BaseStrategy):
    """
    RSI 策略
    基于相对强弱指数生成交易信号
    """

    def __init__(
        self,
        rsi_period: int = 14,
        oversold_threshold: float = 30,
        overbought_threshold: float = 70,
        position_size: int = 10
    ):
        super().__init__("RSIStrategy")
        self.rsi_period = rsi_period
        self.oversold_threshold = oversold_threshold
        self.overbought_threshold = overbought_threshold
        self.position_size = position_size

    def calculate_rsi(self, closes: List[float]) -> float:
        """计算 RSI"""
        if len(closes) < 2:
            return 50.0

        gains = []
        losses = []

        for i in range(1, len(closes)):
            change = closes[i] - closes[i-1]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))

        avg_gain = sum(gains) / len(gains) if gains else 0
        avg_loss = sum(losses) / len(losses) if losses else 0

        if avg_loss == 0:
            return 100.0 if avg_gain > 0 else 50.0

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        return rsi

    def analyze(self, market_data: Dict[str, Any]) -> Signal:
        """分析 RSI"""
        klines = market_data.get("klines", [])

        if len(klines) < self.rsi_period + 1:
            return Signal(action="hold", quantity=0, reason="Insufficient data")

        closes = [k["close"] for k in klines[-(self.rsi_period + 1):]]
        rsi = self.calculate_rsi(closes)

        if rsi < self.oversold_threshold:
            return Signal(
                action="long",
                quantity=self.position_size,
                reason=f"RSI oversold: {rsi:.1f}",
                confidence=min(0.9, 0.5 + (self.oversold_threshold - rsi) * 0.02),
                stop_loss=closes[-1] * 0.97,
                take_profit=closes[-1] * 1.03
            )
        elif rsi > self.overbought_threshold:
            return Signal(
                action="short",
                quantity=self.position_size,
                reason=f"RSI overbought: {rsi:.1f}",
                confidence=min(0.9, 0.5 + (rsi - self.overbought_threshold) * 0.02),
                stop_loss=closes[-1] * 1.03,
                take_profit=closes[-1] * 0.97
            )
        else:
            return Signal(
                action="hold",
                quantity=0,
                reason=f"RSI neutral: {rsi:.1f}"
            )


class MACDStrategy(BaseStrategy):
    """
    MACD 策略
    基于 MACD 交叉生成交易信号
    """

    def __init__(
        self,
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9,
        position_size: int = 10
    ):
        super().__init__("MACDStrategy")
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.signal_period = signal_period
        self.position_size = position_size

    def calculate_ema(self, data: List[float], period: int) -> List[float]:
        """计算 EMA"""
        if len(data) < period:
            return []

        multiplier = 2 / (period + 1)
        ema = [sum(data[:period]) / period]  # 第一个 EMA 用 SMA

        for price in data[period:]:
            ema.append((price - ema[-1]) * multiplier + ema[-1])

        return ema

    def analyze(self, market_data: Dict[str, Any]) -> Signal:
        """分析 MACD"""
        klines = market_data.get("klines", [])

        if len(klines) < self.slow_period + self.signal_period:
            return Signal(action="hold", quantity=0, reason="Insufficient data")

        closes = [k["close"] for k in klines]

        # 计算 MACD
        fast_ema = self.calculate_ema(closes, self.fast_period)
        slow_ema = self.calculate_ema(closes, self.slow_period)

        if len(fast_ema) < len(slow_ema):
            # 对齐长度
            fast_ema = fast_ema[-(len(slow_ema)):]
        else:
            slow_ema = slow_ema[-(len(fast_ema)):]

        macd_line = [f - s for f, s in zip(fast_ema, slow_ema)]
        signal_line = self.calculate_ema(macd_line, self.signal_period)

        if len(signal_line) < 2 or len(macd_line) < len(signal_line) + 1:
            return Signal(action="hold", quantity=0, reason="Insufficient MACD data")

        current_macd = macd_line[-1]
        prev_macd = macd_line[-2]
        current_signal = signal_line[-1]
        prev_signal = signal_line[-2] if len(signal_line) >= 2 else current_signal

        # 检测交叉
        if prev_macd <= prev_signal and current_macd > current_signal:
            # 金叉
            return Signal(
                action="long",
                quantity=self.position_size,
                reason=f"MACD bullish crossover: MACD={current_macd:.4f}",
                confidence=0.7,
                stop_loss=closes[-1] * 0.97,
                take_profit=closes[-1] * 1.03
            )
        elif prev_macd >= prev_signal and current_macd < current_signal:
            # 死叉
            return Signal(
                action="short",
                quantity=self.position_size,
                reason=f"MACD bearish crossover: MACD={current_macd:.4f}",
                confidence=0.7,
                stop_loss=closes[-1] * 1.03,
                take_profit=closes[-1] * 0.97
            )
        else:
            return Signal(
                action="hold",
                quantity=0,
                reason=f"MACD no crossover: MACD={current_macd:.4f}, Signal={current_signal:.4f}"
            )


class CompositeStrategy(BaseStrategy):
    """
    组合策略
    结合多个策略的信号生成最终决策
    """

    def __init__(self, strategies: List[BaseStrategy] = None, position_size: int = 10):
        super().__init__("CompositeStrategy")
        self.strategies = strategies or [
            MomentumStrategy(position_size=position_size),
            RSIStrategy(position_size=position_size),
            MACDStrategy(position_size=position_size)
        ]
        self.position_size = position_size

    def analyze(self, market_data: Dict[str, Any]) -> Signal:
        """分析组合策略"""
        signals = []

        for strategy in self.strategies:
            try:
                signal = strategy.analyze(market_data)
                signals.append(signal)
            except Exception as e:
                logger.warning(f"{strategy.name} failed: {e}")

        if not signals:
            return Signal(action="hold", quantity=0, reason="No valid signals")

        # 统计信号
        long_count = sum(1 for s in signals if s.action == "long")
        short_count = sum(1 for s in signals if s.action == "short")
        total = len(signals)

        # 多数表决
        threshold = 0.5  # 需要超过50%的策略同意

        if long_count / total > threshold:
            avg_confidence = sum(s.confidence for s in signals if s.action == "long") / long_count
            reasons = [s.reason for s in signals if s.action == "long"]
            return Signal(
                action="long",
                quantity=self.position_size,
                reason=f"Composite ({long_count}/{total}): " + "; ".join(reasons[:2]),
                confidence=avg_confidence
            )
        elif short_count / total > threshold:
            avg_confidence = sum(s.confidence for s in signals if s.action == "short") / short_count
            reasons = [s.reason for s in signals if s.action == "short"]
            return Signal(
                action="short",
                quantity=self.position_size,
                reason=f"Composite ({short_count}/{total}): " + "; ".join(reasons[:2]),
                confidence=avg_confidence
            )
        else:
            return Signal(
                action="hold",
                quantity=0,
                reason=f"No consensus: long={long_count}, short={short_count}, hold={total - long_count - short_count}"
            )


# 策略工厂
def get_strategy(name: str, **kwargs) -> BaseStrategy:
    """获取策略实例"""
    strategies = {
        "momentum": MomentumStrategy,
        "mean_reversion": MeanReversionStrategy,
        "rsi": RSIStrategy,
        "macd": MACDStrategy,
        "composite": CompositeStrategy
    }

    strategy_class = strategies.get(name.lower())
    if strategy_class is None:
        raise ValueError(f"Unknown strategy: {name}. Available: {list(strategies.keys())}")

    return strategy_class(**kwargs)
