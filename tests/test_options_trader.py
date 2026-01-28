# -*- coding: utf-8 -*-
"""
期权交易模块单元测试
"""

import pytest
from datetime import date
from unittest.mock import Mock, AsyncMock, patch

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from futu.options_trader import (
    OptionTrader, OptionContract, OptionType, OptionStyle,
    OptionQuote, OptionChain
)


class TestOptionContract:
    """期权合约测试"""

    def test_basic_contract(self):
        """测试基本合约创建"""
        contract = OptionContract(
            underlying="AAPL",
            expiry=date(2025, 1, 17),
            strike=150.0,
            option_type=OptionType.CALL
        )

        assert contract.underlying == "AAPL"
        assert contract.strike == 150.0
        assert contract.option_type == OptionType.CALL
        assert contract.multiplier == 100

    def test_symbol_generation(self):
        """测试期权代码生成"""
        contract = OptionContract(
            underlying="AAPL",
            expiry=date(2025, 1, 17),
            strike=150.0,
            option_type=OptionType.CALL
        )

        # OCC 格式
        symbol = contract.symbol
        assert "AAPL" in symbol
        assert "250117" in symbol
        assert "C" in symbol

    def test_futu_symbol(self):
        """测试富途格式代码"""
        contract = OptionContract(
            underlying="AAPL",
            expiry=date(2025, 1, 17),
            strike=150.0,
            option_type=OptionType.PUT
        )

        futu_symbol = contract.futu_symbol
        assert futu_symbol.startswith("US.")
        assert "AAPL" in futu_symbol
        assert "P" in futu_symbol

    def test_days_to_expiry(self):
        """测试距到期天数"""
        # 使用未来日期
        future_date = date(2026, 12, 31)
        contract = OptionContract(
            underlying="AAPL",
            expiry=future_date,
            strike=150.0,
            option_type=OptionType.CALL
        )

        days = contract.days_to_expiry
        assert days > 0

    def test_is_expired(self):
        """测试是否已到期"""
        # 过去日期
        past_date = date(2020, 1, 1)
        contract = OptionContract(
            underlying="AAPL",
            expiry=past_date,
            strike=150.0,
            option_type=OptionType.CALL
        )

        assert contract.is_expired == True

    def test_from_symbol(self):
        """测试从代码解析"""
        # 标准 OCC 格式
        symbol = "AAPL  250117C00150000"
        contract = OptionContract.from_symbol(symbol)

        assert contract.underlying == "AAPL"
        assert contract.expiry == date(2025, 1, 17)
        assert contract.option_type == OptionType.CALL
        assert contract.strike == 150.0

    def test_from_symbol_put(self):
        """测试解析看跌期权"""
        symbol = "AAPL  250117P00150000"
        contract = OptionContract.from_symbol(symbol)

        assert contract.option_type == OptionType.PUT

    def test_to_dict(self):
        """测试转换为字典"""
        contract = OptionContract(
            underlying="AAPL",
            expiry=date(2025, 1, 17),
            strike=150.0,
            option_type=OptionType.CALL
        )

        data = contract.to_dict()

        assert "symbol" in data
        assert "underlying" in data
        assert "strike" in data
        assert "option_type" in data


class TestOptionQuote:
    """期权行情测试"""

    @pytest.fixture
    def contract(self):
        return OptionContract(
            underlying="AAPL",
            expiry=date(2025, 6, 20),
            strike=150.0,
            option_type=OptionType.CALL
        )

    def test_basic_quote(self, contract):
        """测试基本行情"""
        quote = OptionQuote(
            contract=contract,
            last_price=5.50,
            bid_price=5.40,
            ask_price=5.60,
            volume=1000,
            open_interest=5000,
            underlying_price=155.0
        )

        assert quote.last_price == 5.50
        assert quote.volume == 1000

    def test_spread(self, contract):
        """测试买卖价差"""
        quote = OptionQuote(
            contract=contract,
            last_price=5.50,
            bid_price=5.40,
            ask_price=5.60,
            underlying_price=155.0
        )

        assert quote.spread == 0.20
        assert abs(quote.spread_pct - 0.037) < 0.01

    def test_mid_price(self, contract):
        """测试中间价"""
        quote = OptionQuote(
            contract=contract,
            last_price=5.50,
            bid_price=5.40,
            ask_price=5.60,
            underlying_price=155.0
        )

        assert quote.mid_price == 5.50

    def test_intrinsic_value_call_itm(self, contract):
        """测试看涨期权内在价值（价内）"""
        quote = OptionQuote(
            contract=contract,
            last_price=10.0,
            bid_price=9.90,
            ask_price=10.10,
            underlying_price=160.0  # > 150 strike
        )

        assert quote.intrinsic_value == 10.0  # 160 - 150
        assert quote.is_itm == True

    def test_intrinsic_value_call_otm(self, contract):
        """测试看涨期权内在价值（价外）"""
        quote = OptionQuote(
            contract=contract,
            last_price=2.0,
            bid_price=1.90,
            ask_price=2.10,
            underlying_price=145.0  # < 150 strike
        )

        assert quote.intrinsic_value == 0.0
        assert quote.is_otm == True

    def test_time_value(self, contract):
        """测试时间价值"""
        quote = OptionQuote(
            contract=contract,
            last_price=12.0,
            bid_price=11.90,
            ask_price=12.10,
            underlying_price=160.0
        )

        # 时间价值 = 期权价格 - 内在价值 = 12 - 10 = 2
        assert quote.time_value == 2.0

    def test_is_atm(self, contract):
        """测试是否平价"""
        quote = OptionQuote(
            contract=contract,
            last_price=5.0,
            bid_price=4.90,
            ask_price=5.10,
            underlying_price=150.0  # = strike
        )

        assert quote.is_atm == True


class TestOptionChain:
    """期权链测试"""

    def test_basic_chain(self):
        """测试基本期权链"""
        chain = OptionChain("AAPL")

        assert chain.underlying == "AAPL"
        assert len(chain._calls) == 0
        assert len(chain._puts) == 0

    def test_add_quote(self):
        """测试添加行情"""
        chain = OptionChain("AAPL")

        contract = OptionContract(
            underlying="AAPL",
            expiry=date(2025, 1, 17),
            strike=150.0,
            option_type=OptionType.CALL
        )

        quote = OptionQuote(
            contract=contract,
            last_price=5.0,
            bid_price=4.90,
            ask_price=5.10,
            underlying_price=155.0
        )

        chain.add_quote(quote)

        assert len(chain._calls) == 1
        assert date(2025, 1, 17) in chain.get_expiries()

    def test_get_call_put(self):
        """测试获取看涨/看跌"""
        chain = OptionChain("AAPL")
        expiry = date(2025, 1, 17)
        strike = 150.0

        # 添加看涨
        call_contract = OptionContract("AAPL", expiry, strike, OptionType.CALL)
        call_quote = OptionQuote(call_contract, 5.0, 4.90, 5.10, underlying_price=155.0)
        chain.add_quote(call_quote)

        # 添加看跌
        put_contract = OptionContract("AAPL", expiry, strike, OptionType.PUT)
        put_quote = OptionQuote(put_contract, 2.0, 1.90, 2.10, underlying_price=155.0)
        chain.add_quote(put_quote)

        assert chain.get_call(expiry, strike) is not None
        assert chain.get_put(expiry, strike) is not None

    def test_get_strikes(self):
        """测试获取行权价列表"""
        chain = OptionChain("AAPL")
        expiry = date(2025, 1, 17)

        for strike in [145.0, 150.0, 155.0, 160.0]:
            contract = OptionContract("AAPL", expiry, strike, OptionType.CALL)
            quote = OptionQuote(contract, 1.0, 0.9, 1.1, underlying_price=155.0)
            chain.add_quote(quote)

        strikes = chain.get_strikes(expiry)

        assert len(strikes) == 4
        assert strikes == [145.0, 150.0, 155.0, 160.0]  # 已排序

    def test_get_atm_strike(self):
        """测试获取平价行权价"""
        chain = OptionChain("AAPL")
        expiry = date(2025, 1, 17)

        for strike in [145.0, 150.0, 155.0, 160.0]:
            contract = OptionContract("AAPL", expiry, strike, OptionType.CALL)
            quote = OptionQuote(contract, 1.0, 0.9, 1.1, underlying_price=155.0)
            chain.add_quote(quote)

        atm = chain.get_atm_strike(expiry, 152.0)

        assert atm == 150.0  # 最接近 152

    def test_get_nearest_expiry(self):
        """测试获取最近到期日"""
        chain = OptionChain("AAPL")

        for exp in [date(2025, 1, 17), date(2025, 2, 21), date(2025, 3, 21)]:
            contract = OptionContract("AAPL", exp, 150.0, OptionType.CALL)
            quote = OptionQuote(contract, 1.0, 0.9, 1.1, underlying_price=155.0)
            chain.add_quote(quote)

        nearest = chain.get_nearest_expiry()
        assert nearest == date(2025, 1, 17)


class TestOptionTrader:
    """期权交易器测试"""

    @pytest.fixture
    def trader(self):
        return OptionTrader()

    @pytest.mark.asyncio
    async def test_buy_call(self, trader):
        """测试买入看涨"""
        result = await trader.buy_call(
            underlying="AAPL",
            expiry=date(2025, 1, 17),
            strike=150.0,
            quantity=1
        )

        assert result["success"] == True
        assert result["contract"]["option_type"] == "call"

    @pytest.mark.asyncio
    async def test_buy_put(self, trader):
        """测试买入看跌"""
        result = await trader.buy_put(
            underlying="AAPL",
            expiry=date(2025, 1, 17),
            strike=150.0,
            quantity=1
        )

        assert result["success"] == True
        assert result["contract"]["option_type"] == "put"

    @pytest.mark.asyncio
    async def test_sell_call(self, trader):
        """测试卖出看涨"""
        result = await trader.sell_call(
            underlying="AAPL",
            expiry=date(2025, 1, 17),
            strike=160.0,
            quantity=1
        )

        assert result["success"] == True

    @pytest.mark.asyncio
    async def test_sell_put(self, trader):
        """测试卖出看跌"""
        result = await trader.sell_put(
            underlying="AAPL",
            expiry=date(2025, 1, 17),
            strike=140.0,
            quantity=1
        )

        assert result["success"] == True

    @pytest.mark.asyncio
    async def test_buy_straddle(self, trader):
        """测试买入跨式组合"""
        result = await trader.buy_straddle(
            underlying="AAPL",
            expiry=date(2025, 1, 17),
            strike=150.0,
            quantity=1
        )

        assert result["strategy"] == "long_straddle"
        assert result["success"] == True
        assert result["call"]["success"] == True
        assert result["put"]["success"] == True

    @pytest.mark.asyncio
    async def test_buy_strangle(self, trader):
        """测试买入宽跨式"""
        result = await trader.buy_strangle(
            underlying="AAPL",
            expiry=date(2025, 1, 17),
            call_strike=160.0,
            put_strike=140.0,
            quantity=1
        )

        assert result["strategy"] == "long_strangle"
        assert result["success"] == True

    @pytest.mark.asyncio
    async def test_bull_call_spread(self, trader):
        """测试牛市看涨价差"""
        result = await trader.bull_call_spread(
            underlying="AAPL",
            expiry=date(2025, 1, 17),
            long_strike=150.0,
            short_strike=160.0,
            quantity=1
        )

        assert result["strategy"] == "bull_call_spread"
        assert result["success"] == True

    @pytest.mark.asyncio
    async def test_bear_put_spread(self, trader):
        """测试熊市看跌价差"""
        result = await trader.bear_put_spread(
            underlying="AAPL",
            expiry=date(2025, 1, 17),
            long_strike=150.0,
            short_strike=140.0,
            quantity=1
        )

        assert result["strategy"] == "bear_put_spread"
        assert result["success"] == True

    @pytest.mark.asyncio
    async def test_close_position(self, trader):
        """测试平仓"""
        contract = OptionContract(
            underlying="AAPL",
            expiry=date(2025, 1, 17),
            strike=150.0,
            option_type=OptionType.CALL
        )

        result = await trader.close_position(contract, quantity=1)

        assert result["success"] == True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
