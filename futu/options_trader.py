# -*- coding: utf-8 -*-
"""
期权交易支持
扩展交易系统以支持美股期权交易
"""

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, date
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class OptionType(Enum):
    """期权类型"""
    CALL = "call"
    PUT = "put"


class OptionStyle(Enum):
    """期权风格"""
    AMERICAN = "american"
    EUROPEAN = "european"


@dataclass
class OptionContract:
    """期权合约"""
    underlying: str              # 标的股票 e.g., "AAPL"
    expiry: date                 # 到期日
    strike: float               # 行权价
    option_type: OptionType     # 看涨/看跌

    # 可选属性
    multiplier: int = 100       # 合约乘数
    style: OptionStyle = OptionStyle.AMERICAN

    @property
    def symbol(self) -> str:
        """生成期权代码 (OCC格式)"""
        # 格式: AAPL  240119C00150000
        # 标的(6字符) + 到期日(YYMMDD) + 类型(C/P) + 行权价(8位,含3位小数)
        underlying_padded = self.underlying.ljust(6)
        expiry_str = self.expiry.strftime("%y%m%d")
        type_char = "C" if self.option_type == OptionType.CALL else "P"
        strike_str = f"{int(self.strike * 1000):08d}"
        return f"{underlying_padded}{expiry_str}{type_char}{strike_str}"

    @property
    def futu_symbol(self) -> str:
        """生成富途格式期权代码"""
        # 格式: US.AAPL240119C150000
        expiry_str = self.expiry.strftime("%y%m%d")
        type_char = "C" if self.option_type == OptionType.CALL else "P"
        strike_str = f"{int(self.strike * 1000)}"
        return f"US.{self.underlying}{expiry_str}{type_char}{strike_str}"

    @property
    def is_itm(self) -> bool:
        """是否价内 (需要当前价格)"""
        return False  # 需要外部提供当前价格

    @property
    def days_to_expiry(self) -> int:
        """距到期天数"""
        return (self.expiry - date.today()).days

    @property
    def is_expired(self) -> bool:
        """是否已到期"""
        return date.today() > self.expiry

    @classmethod
    def from_symbol(cls, symbol: str) -> 'OptionContract':
        """从期权代码解析"""
        # 尝试解析 OCC 格式
        pattern = r'^([A-Z]+)\s*(\d{6})([CP])(\d{8})$'
        match = re.match(pattern, symbol.upper().replace('.', '').replace('US', ''))

        if match:
            underlying = match.group(1).strip()
            expiry_str = match.group(2)
            type_char = match.group(3)
            strike_str = match.group(4)

            expiry = datetime.strptime(expiry_str, "%y%m%d").date()
            option_type = OptionType.CALL if type_char == 'C' else OptionType.PUT
            strike = int(strike_str) / 1000

            return cls(
                underlying=underlying,
                expiry=expiry,
                strike=strike,
                option_type=option_type
            )

        raise ValueError(f"Invalid option symbol: {symbol}")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "futu_symbol": self.futu_symbol,
            "underlying": self.underlying,
            "expiry": self.expiry.isoformat(),
            "strike": self.strike,
            "option_type": self.option_type.value,
            "days_to_expiry": self.days_to_expiry,
            "is_expired": self.is_expired,
            "multiplier": self.multiplier,
            "style": self.style.value
        }


@dataclass
class OptionQuote:
    """期权行情"""
    contract: OptionContract
    last_price: float
    bid_price: float
    ask_price: float
    bid_size: int = 0
    ask_size: int = 0
    volume: int = 0
    open_interest: int = 0
    implied_volatility: float = 0.0
    delta: float = 0.0
    gamma: float = 0.0
    theta: float = 0.0
    vega: float = 0.0
    underlying_price: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def spread(self) -> float:
        """买卖价差"""
        return self.ask_price - self.bid_price

    @property
    def spread_pct(self) -> float:
        """买卖价差百分比"""
        if self.bid_price > 0:
            return self.spread / self.bid_price
        return 0.0

    @property
    def mid_price(self) -> float:
        """中间价"""
        return (self.bid_price + self.ask_price) / 2

    @property
    def intrinsic_value(self) -> float:
        """内在价值"""
        if self.contract.option_type == OptionType.CALL:
            return max(0, self.underlying_price - self.contract.strike)
        else:
            return max(0, self.contract.strike - self.underlying_price)

    @property
    def time_value(self) -> float:
        """时间价值"""
        return self.last_price - self.intrinsic_value

    @property
    def is_itm(self) -> bool:
        """是否价内"""
        return self.intrinsic_value > 0

    @property
    def is_otm(self) -> bool:
        """是否价外"""
        return self.intrinsic_value == 0

    @property
    def is_atm(self) -> bool:
        """是否平价 (5%范围内)"""
        diff = abs(self.underlying_price - self.contract.strike)
        return diff / self.underlying_price < 0.05

    def to_dict(self) -> Dict[str, Any]:
        return {
            "contract": self.contract.to_dict(),
            "last_price": self.last_price,
            "bid_price": self.bid_price,
            "ask_price": self.ask_price,
            "spread": round(self.spread, 4),
            "spread_pct": round(self.spread_pct, 4),
            "mid_price": round(self.mid_price, 4),
            "volume": self.volume,
            "open_interest": self.open_interest,
            "implied_volatility": round(self.implied_volatility, 4),
            "greeks": {
                "delta": round(self.delta, 4),
                "gamma": round(self.gamma, 4),
                "theta": round(self.theta, 4),
                "vega": round(self.vega, 4)
            },
            "intrinsic_value": round(self.intrinsic_value, 4),
            "time_value": round(self.time_value, 4),
            "is_itm": self.is_itm,
            "underlying_price": self.underlying_price,
            "timestamp": self.timestamp.isoformat()
        }


class OptionChain:
    """期权链"""

    def __init__(self, underlying: str):
        self.underlying = underlying
        self._calls: Dict[Tuple[date, float], OptionQuote] = {}
        self._puts: Dict[Tuple[date, float], OptionQuote] = {}
        self._expiries: List[date] = []
        self._strikes: Dict[date, List[float]] = {}

    def add_quote(self, quote: OptionQuote):
        """添加期权行情"""
        key = (quote.contract.expiry, quote.contract.strike)

        if quote.contract.option_type == OptionType.CALL:
            self._calls[key] = quote
        else:
            self._puts[key] = quote

        # 更新到期日列表
        if quote.contract.expiry not in self._expiries:
            self._expiries.append(quote.contract.expiry)
            self._expiries.sort()

        # 更新行权价列表
        if quote.contract.expiry not in self._strikes:
            self._strikes[quote.contract.expiry] = []
        if quote.contract.strike not in self._strikes[quote.contract.expiry]:
            self._strikes[quote.contract.expiry].append(quote.contract.strike)
            self._strikes[quote.contract.expiry].sort()

    def get_call(self, expiry: date, strike: float) -> Optional[OptionQuote]:
        """获取看涨期权"""
        return self._calls.get((expiry, strike))

    def get_put(self, expiry: date, strike: float) -> Optional[OptionQuote]:
        """获取看跌期权"""
        return self._puts.get((expiry, strike))

    def get_expiries(self) -> List[date]:
        """获取所有到期日"""
        return self._expiries

    def get_strikes(self, expiry: date) -> List[float]:
        """获取指定到期日的所有行权价"""
        return self._strikes.get(expiry, [])

    def get_atm_strike(self, expiry: date, underlying_price: float) -> Optional[float]:
        """获取最接近平价的行权价"""
        strikes = self.get_strikes(expiry)
        if not strikes:
            return None

        return min(strikes, key=lambda s: abs(s - underlying_price))

    def get_nearest_expiry(self, min_days: int = 0) -> Optional[date]:
        """获取最近到期日"""
        today = date.today()
        for expiry in self._expiries:
            if (expiry - today).days >= min_days:
                return expiry
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "underlying": self.underlying,
            "expiries": [e.isoformat() for e in self._expiries],
            "calls_count": len(self._calls),
            "puts_count": len(self._puts)
        }


class OptionTrader:
    """
    期权交易器
    封装期权特定的交易逻辑
    """

    def __init__(self, executor=None):
        self.executor = executor
        self._chains: Dict[str, OptionChain] = {}

    def get_chain(self, underlying: str) -> OptionChain:
        """获取或创建期权链"""
        if underlying not in self._chains:
            self._chains[underlying] = OptionChain(underlying)
        return self._chains[underlying]

    async def buy_call(
        self,
        underlying: str,
        expiry: date,
        strike: float,
        quantity: int = 1,
        price: Optional[float] = None
    ) -> Dict[str, Any]:
        """买入看涨期权"""
        contract = OptionContract(
            underlying=underlying,
            expiry=expiry,
            strike=strike,
            option_type=OptionType.CALL
        )

        logger.info(f"Buying {quantity} {contract.symbol} @ {price or 'market'}")

        if self.executor:
            result = await self.executor.long(
                contract.futu_symbol,
                quantity,
                price=price
            )
            return {
                "success": result.success,
                "contract": contract.to_dict(),
                "order": result.to_dict()
            }

        return {
            "success": True,
            "contract": contract.to_dict(),
            "order": {"mock": True, "quantity": quantity}
        }

    async def buy_put(
        self,
        underlying: str,
        expiry: date,
        strike: float,
        quantity: int = 1,
        price: Optional[float] = None
    ) -> Dict[str, Any]:
        """买入看跌期权"""
        contract = OptionContract(
            underlying=underlying,
            expiry=expiry,
            strike=strike,
            option_type=OptionType.PUT
        )

        logger.info(f"Buying {quantity} {contract.symbol} @ {price or 'market'}")

        if self.executor:
            result = await self.executor.long(
                contract.futu_symbol,
                quantity,
                price=price
            )
            return {
                "success": result.success,
                "contract": contract.to_dict(),
                "order": result.to_dict()
            }

        return {
            "success": True,
            "contract": contract.to_dict(),
            "order": {"mock": True, "quantity": quantity}
        }

    async def sell_call(
        self,
        underlying: str,
        expiry: date,
        strike: float,
        quantity: int = 1,
        price: Optional[float] = None
    ) -> Dict[str, Any]:
        """卖出看涨期权"""
        contract = OptionContract(
            underlying=underlying,
            expiry=expiry,
            strike=strike,
            option_type=OptionType.CALL
        )

        logger.info(f"Selling {quantity} {contract.symbol} @ {price or 'market'}")

        if self.executor:
            result = await self.executor.short(
                contract.futu_symbol,
                quantity,
                price=price
            )
            return {
                "success": result.success,
                "contract": contract.to_dict(),
                "order": result.to_dict()
            }

        return {
            "success": True,
            "contract": contract.to_dict(),
            "order": {"mock": True, "quantity": quantity}
        }

    async def sell_put(
        self,
        underlying: str,
        expiry: date,
        strike: float,
        quantity: int = 1,
        price: Optional[float] = None
    ) -> Dict[str, Any]:
        """卖出看跌期权"""
        contract = OptionContract(
            underlying=underlying,
            expiry=expiry,
            strike=strike,
            option_type=OptionType.PUT
        )

        logger.info(f"Selling {quantity} {contract.symbol} @ {price or 'market'}")

        if self.executor:
            result = await self.executor.short(
                contract.futu_symbol,
                quantity,
                price=price
            )
            return {
                "success": result.success,
                "contract": contract.to_dict(),
                "order": result.to_dict()
            }

        return {
            "success": True,
            "contract": contract.to_dict(),
            "order": {"mock": True, "quantity": quantity}
        }

    async def close_position(
        self,
        contract: OptionContract,
        quantity: Optional[int] = None
    ) -> Dict[str, Any]:
        """平仓期权"""
        logger.info(f"Closing {quantity or 'all'} {contract.symbol}")

        if self.executor:
            result = await self.executor.flat(
                contract.futu_symbol,
                quantity
            )
            return {
                "success": result.success,
                "contract": contract.to_dict(),
                "order": result.to_dict()
            }

        return {
            "success": True,
            "contract": contract.to_dict(),
            "order": {"mock": True, "closed": True}
        }

    # 常用策略
    async def buy_straddle(
        self,
        underlying: str,
        expiry: date,
        strike: float,
        quantity: int = 1
    ) -> Dict[str, Any]:
        """买入跨式组合 (同时买入看涨和看跌)"""
        call_result = await self.buy_call(underlying, expiry, strike, quantity)
        put_result = await self.buy_put(underlying, expiry, strike, quantity)

        return {
            "strategy": "long_straddle",
            "call": call_result,
            "put": put_result,
            "success": call_result["success"] and put_result["success"]
        }

    async def buy_strangle(
        self,
        underlying: str,
        expiry: date,
        call_strike: float,
        put_strike: float,
        quantity: int = 1
    ) -> Dict[str, Any]:
        """买入宽跨式组合"""
        call_result = await self.buy_call(underlying, expiry, call_strike, quantity)
        put_result = await self.buy_put(underlying, expiry, put_strike, quantity)

        return {
            "strategy": "long_strangle",
            "call": call_result,
            "put": put_result,
            "success": call_result["success"] and put_result["success"]
        }

    async def bull_call_spread(
        self,
        underlying: str,
        expiry: date,
        long_strike: float,
        short_strike: float,
        quantity: int = 1
    ) -> Dict[str, Any]:
        """牛市看涨价差"""
        buy_result = await self.buy_call(underlying, expiry, long_strike, quantity)
        sell_result = await self.sell_call(underlying, expiry, short_strike, quantity)

        return {
            "strategy": "bull_call_spread",
            "long_call": buy_result,
            "short_call": sell_result,
            "success": buy_result["success"] and sell_result["success"]
        }

    async def bear_put_spread(
        self,
        underlying: str,
        expiry: date,
        long_strike: float,
        short_strike: float,
        quantity: int = 1
    ) -> Dict[str, Any]:
        """熊市看跌价差"""
        buy_result = await self.buy_put(underlying, expiry, long_strike, quantity)
        sell_result = await self.sell_put(underlying, expiry, short_strike, quantity)

        return {
            "strategy": "bear_put_spread",
            "long_put": buy_result,
            "short_put": sell_result,
            "success": buy_result["success"] and sell_result["success"]
        }
