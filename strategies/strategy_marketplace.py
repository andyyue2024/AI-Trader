# -*- coding: utf-8 -*-
"""
策略市场模块
支持第三方策略共享和管理
"""

import json
import logging
import hashlib
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class StrategyMeta:
    """策略元数据"""
    id: str
    name: str
    author: str
    version: str
    description: str
    tags: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    downloads: int = 0
    rating: float = 0.0

    # 性能指标
    backtest_sharpe: float = 0.0
    backtest_return: float = 0.0
    backtest_drawdown: float = 0.0

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "author": self.author,
            "version": self.version,
            "description": self.description,
            "tags": self.tags,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "downloads": self.downloads,
            "rating": self.rating,
            "performance": {
                "sharpe": self.backtest_sharpe,
                "return": self.backtest_return,
                "drawdown": self.backtest_drawdown
            }
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "StrategyMeta":
        perf = data.get("performance", {})
        return cls(
            id=data["id"],
            name=data["name"],
            author=data.get("author", "Unknown"),
            version=data.get("version", "1.0.0"),
            description=data.get("description", ""),
            tags=data.get("tags", []),
            downloads=data.get("downloads", 0),
            rating=data.get("rating", 0.0),
            backtest_sharpe=perf.get("sharpe", 0.0),
            backtest_return=perf.get("return", 0.0),
            backtest_drawdown=perf.get("drawdown", 0.0)
        )


class BaseStrategy(ABC):
    """策略基类"""

    def __init__(self, name: str, version: str = "1.0.0"):
        self.name = name
        self.version = version
        self.author = "Unknown"
        self.description = ""
        self.tags: List[str] = []

    @abstractmethod
    def generate_signal(self, market_data: Dict, positions: Dict) -> Dict[str, str]:
        """
        生成交易信号

        Args:
            market_data: 市场数据 {symbol: {price, volume, ...}}
            positions: 当前持仓 {symbol: Position}

        Returns:
            信号字典 {symbol: "long"/"short"/"flat"/"hold"}
        """
        pass

    def on_init(self):
        """初始化回调"""
        pass

    def on_market_open(self):
        """开盘回调"""
        pass

    def on_market_close(self):
        """收盘回调"""
        pass

    def get_meta(self) -> StrategyMeta:
        """获取策略元数据"""
        strategy_id = hashlib.md5(f"{self.name}:{self.version}".encode()).hexdigest()[:12]
        return StrategyMeta(
            id=strategy_id,
            name=self.name,
            author=self.author,
            version=self.version,
            description=self.description,
            tags=self.tags
        )


class StrategyRegistry:
    """策略注册表"""

    _instance = None
    _strategies: Dict[str, type] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def register(cls, strategy_class: type) -> type:
        """注册策略（装饰器）"""
        if not issubclass(strategy_class, BaseStrategy):
            raise ValueError("Strategy must inherit from BaseStrategy")

        instance = strategy_class()
        meta = instance.get_meta()
        cls._strategies[meta.id] = strategy_class
        logger.info(f"Registered strategy: {meta.name} (ID: {meta.id})")
        return strategy_class

    @classmethod
    def get(cls, strategy_id: str) -> Optional[type]:
        """获取策略类"""
        return cls._strategies.get(strategy_id)

    @classmethod
    def list_all(cls) -> List[StrategyMeta]:
        """列出所有策略"""
        result = []
        for strategy_class in cls._strategies.values():
            instance = strategy_class()
            result.append(instance.get_meta())
        return result


class StrategyMarketplace:
    """策略市场"""

    def __init__(self, storage_dir: str = "./strategies"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.index_file = self.storage_dir / "index.json"
        self.strategies: Dict[str, StrategyMeta] = {}
        self._load_index()

    def _load_index(self):
        """加载策略索引"""
        if self.index_file.exists():
            with open(self.index_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for item in data.get("strategies", []):
                    meta = StrategyMeta.from_dict(item)
                    self.strategies[meta.id] = meta

    def _save_index(self):
        """保存策略索引"""
        data = {
            "updated_at": datetime.now().isoformat(),
            "count": len(self.strategies),
            "strategies": [m.to_dict() for m in self.strategies.values()]
        }
        with open(self.index_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def publish(self, strategy: BaseStrategy, code: str = None) -> StrategyMeta:
        """发布策略到市场"""
        meta = strategy.get_meta()

        # 保存策略代码
        if code:
            code_file = self.storage_dir / f"{meta.id}.py"
            with open(code_file, 'w', encoding='utf-8') as f:
                f.write(code)

        # 更新索引
        self.strategies[meta.id] = meta
        self._save_index()

        logger.info(f"Published strategy: {meta.name} (ID: {meta.id})")
        return meta

    def download(self, strategy_id: str) -> Optional[str]:
        """下载策略代码"""
        if strategy_id not in self.strategies:
            logger.warning(f"Strategy not found: {strategy_id}")
            return None

        code_file = self.storage_dir / f"{strategy_id}.py"
        if not code_file.exists():
            logger.warning(f"Strategy code not found: {strategy_id}")
            return None

        # 增加下载计数
        self.strategies[strategy_id].downloads += 1
        self._save_index()

        with open(code_file, 'r', encoding='utf-8') as f:
            return f.read()

    def search(
        self,
        query: str = None,
        tags: List[str] = None,
        min_rating: float = 0.0,
        sort_by: str = "downloads"
    ) -> List[StrategyMeta]:
        """搜索策略"""
        results = list(self.strategies.values())

        # 按关键词过滤
        if query:
            query = query.lower()
            results = [
                s for s in results
                if query in s.name.lower() or query in s.description.lower()
            ]

        # 按标签过滤
        if tags:
            results = [
                s for s in results
                if any(t in s.tags for t in tags)
            ]

        # 按评分过滤
        results = [s for s in results if s.rating >= min_rating]

        # 排序
        if sort_by == "downloads":
            results.sort(key=lambda s: s.downloads, reverse=True)
        elif sort_by == "rating":
            results.sort(key=lambda s: s.rating, reverse=True)
        elif sort_by == "sharpe":
            results.sort(key=lambda s: s.backtest_sharpe, reverse=True)
        elif sort_by == "return":
            results.sort(key=lambda s: s.backtest_return, reverse=True)

        return results

    def rate(self, strategy_id: str, rating: float):
        """给策略评分"""
        if strategy_id in self.strategies:
            # 简单平均（实际应该用加权平均）
            current = self.strategies[strategy_id].rating
            new_rating = (current + rating) / 2 if current > 0 else rating
            self.strategies[strategy_id].rating = min(5.0, max(0.0, new_rating))
            self._save_index()

    def get_leaderboard(self, metric: str = "sharpe", limit: int = 10) -> List[StrategyMeta]:
        """获取策略排行榜"""
        results = list(self.strategies.values())

        if metric == "sharpe":
            results.sort(key=lambda s: s.backtest_sharpe, reverse=True)
        elif metric == "return":
            results.sort(key=lambda s: s.backtest_return, reverse=True)
        elif metric == "drawdown":
            results.sort(key=lambda s: s.backtest_drawdown)  # 越小越好
        elif metric == "downloads":
            results.sort(key=lambda s: s.downloads, reverse=True)

        return results[:limit]


# ============ 内置策略示例 ============

@StrategyRegistry.register
class MomentumStrategy(BaseStrategy):
    """动量策略"""

    def __init__(self):
        super().__init__("Momentum Strategy", "1.0.0")
        self.author = "AI-Trader"
        self.description = "Simple momentum-based trading strategy"
        self.tags = ["momentum", "trend-following", "beginner"]

    def generate_signal(self, market_data: Dict, positions: Dict) -> Dict[str, str]:
        signals = {}
        for symbol, data in market_data.items():
            if symbol not in positions:
                signals[symbol] = "long"  # 简单示例：无持仓则买入
            else:
                signals[symbol] = "hold"
        return signals


@StrategyRegistry.register
class MeanReversionStrategy(BaseStrategy):
    """均值回归策略"""

    def __init__(self):
        super().__init__("Mean Reversion Strategy", "1.0.0")
        self.author = "AI-Trader"
        self.description = "Mean reversion strategy based on Bollinger Bands concept"
        self.tags = ["mean-reversion", "contrarian", "intermediate"]

    def generate_signal(self, market_data: Dict, positions: Dict) -> Dict[str, str]:
        signals = {}
        for symbol, data in market_data.items():
            # 简单示例：价格低于某个阈值则买入
            price = data.get("price", 0)
            avg_price = data.get("avg_price", price)

            if price < avg_price * 0.98:  # 低于均价2%
                signals[symbol] = "long"
            elif price > avg_price * 1.02:  # 高于均价2%
                signals[symbol] = "short" if symbol in positions else "hold"
            else:
                signals[symbol] = "hold"

        return signals


@StrategyRegistry.register
class BreakoutStrategy(BaseStrategy):
    """突破策略"""

    def __init__(self):
        super().__init__("Breakout Strategy", "1.0.0")
        self.author = "AI-Trader"
        self.description = "Price breakout strategy for volatile markets"
        self.tags = ["breakout", "volatility", "advanced"]

    def generate_signal(self, market_data: Dict, positions: Dict) -> Dict[str, str]:
        signals = {}
        for symbol, data in market_data.items():
            price = data.get("price", 0)
            high_20 = data.get("high_20", price)  # 20日最高
            low_20 = data.get("low_20", price)    # 20日最低

            if price >= high_20:  # 突破20日高点
                signals[symbol] = "long"
            elif price <= low_20:  # 跌破20日低点
                signals[symbol] = "short" if symbol in positions else "flat"
            else:
                signals[symbol] = "hold"

        return signals


if __name__ == "__main__":
    # 测试策略市场
    marketplace = StrategyMarketplace()

    # 列出所有注册的策略
    print("=== Registered Strategies ===")
    for meta in StrategyRegistry.list_all():
        print(f"  - {meta.name} (ID: {meta.id})")

    # 发布策略到市场
    momentum = MomentumStrategy()
    marketplace.publish(momentum)

    mean_rev = MeanReversionStrategy()
    marketplace.publish(mean_rev)

    breakout = BreakoutStrategy()
    marketplace.publish(breakout)

    # 搜索策略
    print("\n=== Search Results ===")
    results = marketplace.search(tags=["momentum"])
    for meta in results:
        print(f"  - {meta.name}: {meta.description}")

    # 排行榜
    print("\n=== Leaderboard ===")
    for i, meta in enumerate(marketplace.get_leaderboard("downloads", 5), 1):
        print(f"  {i}. {meta.name} ({meta.downloads} downloads)")
