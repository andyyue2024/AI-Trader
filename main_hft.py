# -*- coding: utf-8 -*-
"""
AI-Trader 高频交易主程序
基于富途 OpenD 实现 TQQQ/QQQ 等美股高频交易
目标：1分钟行情->模型->下单全流程 ≤ 1s
"""

import asyncio
import json
import logging
import os
import signal
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class HighFrequencyTrader:
    """
    高频交易器
    实现 1分钟行情 -> AI模型决策 -> 下单 的全流程
    """

    def __init__(
        self,
        symbols: List[str] = None,
        config_path: str = None,
        dry_run: bool = False
    ):
        """
        初始化高频交易器

        Args:
            symbols: 交易标的列表，默认 ["TQQQ", "QQQ"]
            config_path: 配置文件路径
            dry_run: 是否模拟运行（不实际下单）
        """
        self.symbols = symbols or ["TQQQ", "QQQ"]
        self.config_path = config_path
        self.dry_run = dry_run
        self.running = False

        # 组件
        self._executor = None
        self._subscriber = None
        self._risk_manager = None
        self._metrics_exporter = None
        self._feishu_alert = None
        self._agent = None

        # 配置
        self.config = self._load_config()

        # 性能统计
        self._loop_times: List[float] = []
        self._decision_times: List[float] = []
        self._execution_times: List[float] = []

    def _load_config(self) -> Dict[str, Any]:
        """加载配置"""
        default_config = {
            "trading": {
                "initial_cash": 50000.0,
                "max_position_per_symbol": 0.20,  # 单个标的最大仓位20%
                "trading_interval": 60,           # 交易间隔(秒)
                "enable_premarket": True,
                "enable_afterhours": True
            },
            "risk": {
                "daily_loss_limit": 0.03,         # 日内亏损限制3%
                "max_drawdown": 0.15,             # 最大回撤15%
                "max_slippage": 0.002,            # 最大滑点0.2%
                "auto_circuit_breaker": True
            },
            "performance": {
                "target_loop_time_ms": 1000,      # 目标循环时间1s
                "target_order_latency_ms": 1.4    # 目标下单延迟0.0014s
            },
            "monitoring": {
                "metrics_port": 9090,
                "enable_feishu": True,
                "feishu_webhook": os.getenv("FEISHU_WEBHOOK_URL", "")
            },
            "model": {
                "name": "gpt-4",
                "base_url": os.getenv("OPENAI_API_BASE"),
                "api_key": os.getenv("OPENAI_API_KEY"),
                "max_tokens": 1000
            }
        }

        if self.config_path and Path(self.config_path).exists():
            with open(self.config_path, "r", encoding="utf-8") as f:
                user_config = json.load(f)
                # 合并配置
                for key in user_config:
                    if key in default_config and isinstance(default_config[key], dict):
                        default_config[key].update(user_config[key])
                    else:
                        default_config[key] = user_config[key]

        return default_config

    async def initialize(self):
        """初始化所有组件"""
        logger.info("=" * 60)
        logger.info("🚀 Initializing AI-Trader High Frequency Trading System")
        logger.info(f"   Symbols: {self.symbols}")
        logger.info(f"   Dry Run: {self.dry_run}")
        logger.info("=" * 60)

        # 1. 初始化富途连接
        logger.info("📡 Initializing Futu OpenD connection...")
        from futu.opend_client import init_opend, OpenDConfig

        opend_config = OpenDConfig(
            host=os.getenv("OPEND_HOST", "127.0.0.1"),
            port=int(os.getenv("OPEND_PORT", "11111")),
            trd_env=int(os.getenv("OPEND_TRD_ENV", "1")),  # 默认模拟
            password=os.getenv("OPEND_TRADE_PASSWORD"),
            pool_size=3
        )

        if not init_opend(opend_config):
            logger.warning("⚠️ OpenD connection failed, running in simulation mode")
        else:
            logger.info("✅ OpenD connected")

        # 2. 初始化交易执行器
        logger.info("💹 Initializing trade executor...")
        from futu.trade_executor import FutuTradeExecutor

        self._executor = FutuTradeExecutor(
            trd_env=opend_config.trd_env,
            max_slippage=self.config["risk"]["max_slippage"],
            enable_short=True
        )
        logger.info("✅ Trade executor ready")

        # 3. 初始化行情订阅
        logger.info("📊 Initializing quote subscriber...")
        from futu.quote_subscriber import FutuQuoteSubscriber

        self._subscriber = FutuQuoteSubscriber(symbols=self.symbols)
        await self._subscriber.subscribe(self.symbols)
        logger.info("✅ Quote subscriber ready")

        # 4. 初始化风控模块
        logger.info("🛡️ Initializing risk manager...")
        from risk_control.risk_manager import RiskManager, RiskConfig

        self._risk_manager = RiskManager(RiskConfig(
            daily_loss_threshold=self.config["risk"]["daily_loss_limit"],
            max_drawdown=self.config["risk"]["max_drawdown"],
            max_slippage=self.config["risk"]["max_slippage"]
        ))
        self._risk_manager.initialize(self.config["trading"]["initial_cash"])
        logger.info("✅ Risk manager ready")

        # 5. 初始化监控
        logger.info("📈 Initializing monitoring...")
        from monitoring.metrics_exporter import start_metrics_server
        from monitoring.feishu_alert import FeishuAlert, AlertConfig

        self._metrics_exporter = start_metrics_server(
            port=self.config["monitoring"]["metrics_port"]
        )

        if self.config["monitoring"]["enable_feishu"] and self.config["monitoring"]["feishu_webhook"]:
            self._feishu_alert = FeishuAlert(AlertConfig(
                webhook_url=self.config["monitoring"]["feishu_webhook"]
            ))
            logger.info("✅ Feishu alert enabled")

        logger.info("✅ Monitoring ready")

        # 6. 初始化绩效分析器
        logger.info("📊 Initializing performance analyzer...")
        from risk_control.performance_analyzer import PerformanceAnalyzer
        self._performance_analyzer = PerformanceAnalyzer(
            initial_equity=self.config["trading"]["initial_cash"]
        )
        logger.info("✅ Performance analyzer ready")

        # 7. 初始化时段管理器
        logger.info("⏰ Initializing session manager...")
        from futu.session_manager import SessionManager, MarketType
        self._session_manager = SessionManager(MarketType.US_STOCK)
        session_status = self._session_manager.get_status()
        logger.info(f"   Current session: {session_status['current_session']}")
        logger.info(f"   Can trade: {session_status['can_trade']}")
        logger.info("✅ Session manager ready")

        # 8. 设置风控回调
        self._setup_risk_callbacks()

        logger.info("=" * 60)
        logger.info("✅ All components initialized")
        logger.info("=" * 60)

    def _setup_risk_callbacks(self):
        """设置风控回调"""
        def on_halt(source: str, reason: str):
            logger.error(f"🚨 Trading halted by {source}: {reason}")
            if self._feishu_alert:
                self._feishu_alert.send_critical(
                    title="AI-Trader 交易熔断",
                    content=f"触发源: {source}\n原因: {reason}",
                    symbols=",".join(self.symbols)
                )

        def on_slippage_violation(violation):
            logger.warning(f"⚠️ Slippage violation: {violation.symbol} {violation.slippage:.4%}")
            if self._feishu_alert:
                self._feishu_alert.send_warning(
                    title="AI-Trader 滑点超限",
                    content=f"标的: {violation.symbol}\n滑点: {violation.slippage:.4%}\n阈值: {violation.threshold:.4%}"
                )

        self._risk_manager.register_callback("on_halt", on_halt)
        self._risk_manager.register_callback("on_slippage_violation", on_slippage_violation)

    async def get_market_data(self, symbol: str) -> Dict[str, Any]:
        """获取市场数据"""
        quote = await self._subscriber.get_quote(symbol)
        klines = await self._subscriber.get_klines(symbol, "K_1M", 100)

        return {
            "symbol": symbol,
            "current_price": quote.last_price if quote else 0,
            "bid": quote.bid_price if quote else 0,
            "ask": quote.ask_price if quote else 0,
            "volume": quote.volume if quote else 0,
            "session": quote.session.value if quote else "unknown",
            "klines": [k.to_dict() for k in klines[-20:]] if klines else []
        }

    async def make_decision(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        AI 决策

        Returns:
            Dict with keys: action (long/short/flat/hold), quantity, reason
        """
        start = time.perf_counter()

        klines = market_data.get("klines", [])

        if len(klines) < 5:
            return {"action": "hold", "reason": "Insufficient data"}

        # 使用策略模块进行决策
        if hasattr(self, '_strategy') and self._strategy:
            signal = self._strategy.analyze(market_data)
            decision = signal.to_dict()
        else:
            # 默认使用组合策略
            from futu.strategies import CompositeStrategy
            if not hasattr(self, '_default_strategy'):
                self._default_strategy = CompositeStrategy(position_size=10)

            signal = self._default_strategy.analyze(market_data)
            decision = signal.to_dict()

        decision_time = (time.perf_counter() - start) * 1000
        self._decision_times.append(decision_time)
        decision["decision_time_ms"] = decision_time

        return decision

    async def execute_decision(
        self,
        symbol: str,
        decision: Dict[str, Any],
        market_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """执行交易决策"""
        action = decision.get("action", "hold")
        quantity = decision.get("quantity", 0)

        if action == "hold" or quantity <= 0:
            return None

        if self.dry_run:
            logger.info(f"[DRY RUN] Would execute {action} {quantity} {symbol}")
            return {"dry_run": True, "action": action, "quantity": quantity}

        # 风控检查
        risk_check = self._risk_manager.pre_trade_check(
            symbol=symbol,
            side=action,
            quantity=quantity,
            price=market_data.get("current_price", 0)
        )

        if not risk_check.allowed:
            logger.warning(f"Trade rejected: {risk_check.reasons}")
            return {"rejected": True, "reasons": risk_check.reasons}

        start = time.perf_counter()

        try:
            if action == "long":
                result = await self._executor.long(symbol, quantity)
            elif action == "short":
                result = await self._executor.short(symbol, quantity)
            elif action == "flat":
                result = await self._executor.flat(symbol, quantity)
            else:
                return None

            execution_time = (time.perf_counter() - start) * 1000
            self._execution_times.append(execution_time)

            # 更新风控
            if result.success:
                self._risk_manager.post_trade_check(
                    symbol=symbol,
                    expected_price=market_data.get("current_price", 0),
                    executed_price=result.filled_price,
                    order_id=result.order_id
                )

                # 记录到绩效分析器
                if hasattr(self, '_performance_analyzer') and self._performance_analyzer:
                    self._performance_analyzer.record_order(
                        submitted=True,
                        filled=True,
                        slippage=result.slippage if hasattr(result, 'slippage') else 0.0
                    )

            return result.to_dict()

        except Exception as e:
            logger.error(f"Execution failed: {e}")
            return {"error": str(e)}

    async def trading_loop(self):
        """主交易循环"""
        interval = self.config["trading"]["trading_interval"]

        while self.running:
            loop_start = time.perf_counter()

            try:
                # 检查是否可以交易
                if not self._risk_manager.circuit_breaker.can_trade():
                    logger.warning("Trading halted by circuit breaker")
                    await asyncio.sleep(60)
                    continue

                # 使用时段管理器检查交易时段
                if hasattr(self, '_session_manager') and self._session_manager:
                    current_session = self._session_manager.get_current_session()
                    can_trade = self._session_manager.can_trade()

                    if not can_trade:
                        next_session, time_to_next = self._session_manager.get_time_to_next_session()
                        wait_seconds = min(60, time_to_next.total_seconds())
                        logger.info(f"Market {current_session.value}, next: {next_session.value} in {time_to_next}")
                        await asyncio.sleep(wait_seconds)
                        continue

                    # 检查盘前/盘后是否启用
                    if current_session.value == "pre_market" and not self.config["trading"]["enable_premarket"]:
                        logger.info("Pre-market trading disabled, waiting...")
                        await asyncio.sleep(60)
                        continue

                    if current_session.value == "after_hours" and not self.config["trading"]["enable_afterhours"]:
                        logger.info("After-hours trading disabled, waiting...")
                        await asyncio.sleep(60)
                        continue
                else:
                    # 降级：使用订阅器检查
                    session = self._subscriber.get_current_session()
                    if session.value == "closed":
                        logger.info("Market closed, waiting...")
                        await asyncio.sleep(60)
                        continue

                # 遍历所有标的
                for symbol in self.symbols:
                    try:
                        # 1. 获取市场数据
                        market_data = await self.get_market_data(symbol)

                        # 2. AI 决策
                        decision = await self.make_decision(market_data)

                        if decision and decision.get("action") != "hold":
                            logger.info(f"📊 {symbol}: {decision}")

                            # 3. 执行交易
                            result = await self.execute_decision(symbol, decision, market_data)

                            if result:
                                logger.info(f"💹 Execution result: {result}")

                    except Exception as e:
                        logger.error(f"Error processing {symbol}: {e}")

                # 更新指标
                loop_time = (time.perf_counter() - loop_start) * 1000
                self._loop_times.append(loop_time)
                self._update_metrics(loop_time)

                # 检查性能
                target_time = self.config["performance"]["target_loop_time_ms"]
                if loop_time > target_time:
                    logger.warning(f"⚠️ Loop time {loop_time:.1f}ms exceeded target {target_time}ms")

                # 等待下一个周期
                elapsed = time.perf_counter() - loop_start
                wait_time = max(0, interval - elapsed)
                if wait_time > 0:
                    await asyncio.sleep(wait_time)

            except Exception as e:
                logger.error(f"Trading loop error: {e}")
                if self._feishu_alert:
                    self._feishu_alert.send_error(
                        title="AI-Trader 交易循环异常",
                        content=str(e)
                    )
                await asyncio.sleep(5)

    def _update_metrics(self, loop_time: float):
        """更新监控指标"""
        if not self._metrics_exporter:
            return

        # 计算统计
        avg_loop = sum(self._loop_times[-100:]) / max(1, len(self._loop_times[-100:]))
        avg_decision = sum(self._decision_times[-100:]) / max(1, len(self._decision_times[-100:]))
        avg_execution = sum(self._execution_times[-100:]) / max(1, len(self._execution_times[-100:]))

        # 更新指标
        risk_status = self._risk_manager.get_status()
        exec_metrics = self._executor.get_execution_metrics()

        self._metrics_exporter.update_metrics(
            total_equity=risk_status["circuit_breaker"]["stats"]["current_equity"],
            daily_return=risk_status["circuit_breaker"]["stats"]["daily_return"],
            current_drawdown=risk_status["drawdown"]["current_drawdown"],
            max_drawdown=risk_status["drawdown"]["max_recorded_drawdown"],
            risk_level=risk_status["risk_level"],
            circuit_breaker_status=risk_status["circuit_breaker"]["state"],
            total_trades=exec_metrics["total_orders"],
            fill_rate=exec_metrics["success_rate"],
            avg_slippage=exec_metrics["average_slippage"],
            avg_order_latency_ms=avg_execution,
            is_trading=self.running
        )

    async def start(self):
        """启动交易"""
        self.running = True

        # 发送启动通知
        if self._feishu_alert:
            self._feishu_alert.send_info(
                title="AI-Trader 启动",
                content=f"交易标的: {', '.join(self.symbols)}\n模式: {'模拟' if self.dry_run else '实盘'}"
            )

        logger.info("🚀 Starting trading loop...")

        try:
            await self.trading_loop()
        except KeyboardInterrupt:
            logger.info("Received interrupt, stopping...")
        finally:
            await self.stop()

    async def stop(self):
        """停止交易"""
        self.running = False

        logger.info("Stopping trader...")

        # 平掉所有仓位（可选）
        # for symbol in self.symbols:
        #     await self._executor.flat(symbol)

        # 停止订阅
        if self._subscriber:
            await self._subscriber.close()

        # 关闭执行器
        if self._executor:
            await self._executor.close()

        # 停止指标服务
        if self._metrics_exporter:
            self._metrics_exporter.stop_server()

        # 发送停止通知
        if self._feishu_alert:
            self._feishu_alert.send_info(
                title="AI-Trader 停止",
                content="交易已停止"
            )

        logger.info("✅ Trader stopped")

    def get_performance_stats(self) -> Dict[str, Any]:
        """获取性能统计"""
        stats = {
            "loop_times": {
                "count": len(self._loop_times),
                "avg_ms": sum(self._loop_times) / max(1, len(self._loop_times)),
                "max_ms": max(self._loop_times) if self._loop_times else 0,
                "min_ms": min(self._loop_times) if self._loop_times else 0
            },
            "decision_times": {
                "count": len(self._decision_times),
                "avg_ms": sum(self._decision_times) / max(1, len(self._decision_times)),
                "max_ms": max(self._decision_times) if self._decision_times else 0
            },
            "execution_times": {
                "count": len(self._execution_times),
                "avg_ms": sum(self._execution_times) / max(1, len(self._execution_times)),
                "max_ms": max(self._execution_times) if self._execution_times else 0
            },
            "execution_metrics": self._executor.get_execution_metrics() if self._executor else {},
            "risk_status": self._risk_manager.get_status() if self._risk_manager else {}
        }

        # 添加绩效分析指标
        if hasattr(self, '_performance_analyzer') and self._performance_analyzer:
            perf_metrics = self._performance_analyzer.get_performance_metrics()
            stats["performance"] = perf_metrics.to_dict()
            stats["targets_met"] = perf_metrics.meets_targets(
                target_sharpe=2.0,
                target_max_dd=0.15,
                target_daily_volume=50000,
                target_fill_rate=0.95
            )

        # 添加时段信息
        if hasattr(self, '_session_manager') and self._session_manager:
            stats["session"] = self._session_manager.get_status()

        return stats


async def main():
    """主入口"""
    import argparse

    parser = argparse.ArgumentParser(description="AI-Trader High Frequency Trading")
    parser.add_argument(
        "--symbols",
        nargs="+",
        default=["TQQQ", "QQQ"],
        help="Trading symbols (default: TQQQ QQQ)"
    )
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Config file path"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run in simulation mode without actual orders"
    )

    args = parser.parse_args()

    trader = HighFrequencyTrader(
        symbols=args.symbols,
        config_path=args.config,
        dry_run=args.dry_run
    )

    # 设置信号处理
    def signal_handler(sig, frame):
        logger.info("Received signal, stopping...")
        trader.running = False

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        await trader.initialize()
        await trader.start()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise
    finally:
        # 打印性能统计
        stats = trader.get_performance_stats()
        logger.info("=" * 60)
        logger.info("Performance Statistics:")
        logger.info(json.dumps(stats, indent=2, default=str))
        logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
