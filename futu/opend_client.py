# -*- coding: utf-8 -*-
"""
Futu OpenD 客户端管理器
实现连接池、心跳检测、自动重连机制
支持高频交易场景下的稳定连接
"""

import asyncio
import logging
import os
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from queue import Queue, Empty
from typing import Any, Callable, Dict, List, Optional, Tuple
from contextlib import contextmanager
from datetime import datetime, timedelta

try:
    from futu import (
        OpenQuoteContext, OpenSecTradeContext,
        RET_OK, RET_ERROR,
        TrdEnv, TrdMarket, SecurityFirm,
        KLType, SubType, AuType,
        OrderType as FutuOrderType,
        OrderStatus, TrdSide,
        ModifyOrderOp, TimeInForce
    )
    FUTU_AVAILABLE = True
except ImportError:
    FUTU_AVAILABLE = False
    # Mock classes for testing without futu-api installed
    class MockContext:
        def close(self): pass
    OpenQuoteContext = MockContext
    OpenSecTradeContext = MockContext
    RET_OK, RET_ERROR = 0, -1

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ConnectionState(Enum):
    """连接状态枚举"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    ERROR = "error"


@dataclass
class OpenDConfig:
    """OpenD 连接配置"""
    host: str = "127.0.0.1"
    port: int = 11111
    trd_env: int = 1  # 0=真实环境, 1=模拟环境
    market: str = "US"  # US/HK/CN
    security_firm: str = "FUTUINC"
    is_encrypt: bool = False
    rsa_file: Optional[str] = None
    password: Optional[str] = None
    password_md5: Optional[str] = None

    # 连接池配置
    pool_size: int = 3
    max_retries: int = 5
    retry_delay: float = 1.0
    heartbeat_interval: float = 30.0
    connection_timeout: float = 10.0


@dataclass
class ConnectionMetrics:
    """连接指标统计"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    reconnect_count: int = 0
    last_heartbeat: Optional[datetime] = None
    average_latency_ms: float = 0.0
    latency_samples: List[float] = field(default_factory=list)

    def record_latency(self, latency_ms: float, max_samples: int = 1000):
        """记录延迟"""
        self.latency_samples.append(latency_ms)
        if len(self.latency_samples) > max_samples:
            self.latency_samples = self.latency_samples[-max_samples:]
        self.average_latency_ms = sum(self.latency_samples) / len(self.latency_samples)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "success_rate": self.successful_requests / max(1, self.total_requests),
            "reconnect_count": self.reconnect_count,
            "average_latency_ms": round(self.average_latency_ms, 3),
            "last_heartbeat": self.last_heartbeat.isoformat() if self.last_heartbeat else None
        }


class OpenDClient:
    """
    OpenD 单连接客户端
    封装行情和交易上下文，提供统一接口
    """

    def __init__(self, config: OpenDConfig):
        self.config = config
        self.quote_ctx: Optional[OpenQuoteContext] = None
        self.trade_ctx: Optional[OpenSecTradeContext] = None
        self.state = ConnectionState.DISCONNECTED
        self.metrics = ConnectionMetrics()
        self._lock = threading.RLock()
        self._callbacks: Dict[str, List[Callable]] = {}

    def connect(self) -> bool:
        """建立连接"""
        with self._lock:
            if self.state == ConnectionState.CONNECTED:
                return True

            self.state = ConnectionState.CONNECTING
            start_time = time.time()

            try:
                if not FUTU_AVAILABLE:
                    logger.warning("futu-api not installed, using mock connection")
                    self.state = ConnectionState.CONNECTED
                    return True

                # 创建行情上下文
                self.quote_ctx = OpenQuoteContext(
                    host=self.config.host,
                    port=self.config.port,
                    is_encrypt=self.config.is_encrypt
                )

                # 创建交易上下文
                trd_env = TrdEnv.REAL if self.config.trd_env == 0 else TrdEnv.SIMULATE
                trd_market = getattr(TrdMarket, self.config.market, TrdMarket.US)

                self.trade_ctx = OpenSecTradeContext(
                    host=self.config.host,
                    port=self.config.port,
                    is_encrypt=self.config.is_encrypt,
                    security_firm=getattr(SecurityFirm, self.config.security_firm, SecurityFirm.FUTUINC)
                )

                # 解锁交易（如需要）
                if self.config.password:
                    ret, data = self.trade_ctx.unlock_trade(
                        password=self.config.password,
                        password_md5=self.config.password_md5,
                        is_unlock=True
                    )
                    if ret != RET_OK:
                        logger.error(f"Failed to unlock trade: {data}")
                        raise ConnectionError(f"Trade unlock failed: {data}")

                self.state = ConnectionState.CONNECTED
                latency = (time.time() - start_time) * 1000
                self.metrics.record_latency(latency)
                logger.info(f"OpenD connected in {latency:.2f}ms")

                self._trigger_callback("on_connect")
                return True

            except Exception as e:
                self.state = ConnectionState.ERROR
                logger.error(f"Connection failed: {e}")
                self._trigger_callback("on_error", e)
                return False

    def disconnect(self):
        """断开连接"""
        with self._lock:
            if self.quote_ctx:
                try:
                    self.quote_ctx.close()
                except:
                    pass
                self.quote_ctx = None

            if self.trade_ctx:
                try:
                    self.trade_ctx.close()
                except:
                    pass
                self.trade_ctx = None

            self.state = ConnectionState.DISCONNECTED
            self._trigger_callback("on_disconnect")
            logger.info("OpenD disconnected")

    def reconnect(self) -> bool:
        """重连"""
        self.state = ConnectionState.RECONNECTING
        self.metrics.reconnect_count += 1
        self.disconnect()

        for attempt in range(self.config.max_retries):
            logger.info(f"Reconnect attempt {attempt + 1}/{self.config.max_retries}")
            if self.connect():
                return True
            time.sleep(self.config.retry_delay * (2 ** attempt))  # 指数退避

        self.state = ConnectionState.ERROR
        return False

    def heartbeat(self) -> bool:
        """心跳检测"""
        if not FUTU_AVAILABLE or self.state != ConnectionState.CONNECTED:
            return False

        try:
            # 使用简单的API调用作为心跳
            ret, data = self.quote_ctx.get_global_state()
            if ret == RET_OK:
                self.metrics.last_heartbeat = datetime.now()
                return True
            return False
        except Exception as e:
            logger.warning(f"Heartbeat failed: {e}")
            return False

    def register_callback(self, event: str, callback: Callable):
        """注册事件回调"""
        if event not in self._callbacks:
            self._callbacks[event] = []
        self._callbacks[event].append(callback)

    def _trigger_callback(self, event: str, *args):
        """触发事件回调"""
        for callback in self._callbacks.get(event, []):
            try:
                callback(*args)
            except Exception as e:
                logger.error(f"Callback error for {event}: {e}")

    @property
    def is_connected(self) -> bool:
        return self.state == ConnectionState.CONNECTED


class OpenDConnectionPool:
    """
    OpenD 连接池
    管理多个连接，支持负载均衡和故障转移
    """

    def __init__(self, config: OpenDConfig):
        self.config = config
        self._connections: List[OpenDClient] = []
        self._available: Queue = Queue()
        self._lock = threading.Lock()
        self._heartbeat_thread: Optional[threading.Thread] = None
        self._running = False
        self._initialized = False

    def initialize(self) -> bool:
        """初始化连接池"""
        if self._initialized:
            return True

        logger.info(f"Initializing connection pool with {self.config.pool_size} connections")

        for i in range(self.config.pool_size):
            client = OpenDClient(self.config)
            if client.connect():
                self._connections.append(client)
                self._available.put(client)
            else:
                logger.warning(f"Failed to create connection {i + 1}")

        if not self._connections:
            logger.error("No connections available in pool")
            return False

        # 启动心跳线程
        self._running = True
        self._heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self._heartbeat_thread.start()

        self._initialized = True
        logger.info(f"Connection pool initialized with {len(self._connections)} connections")
        return True

    def shutdown(self):
        """关闭连接池"""
        self._running = False
        if self._heartbeat_thread:
            self._heartbeat_thread.join(timeout=5)

        for client in self._connections:
            client.disconnect()

        self._connections.clear()
        self._initialized = False
        logger.info("Connection pool shutdown")

    @contextmanager
    def get_connection(self, timeout: float = 5.0):
        """获取连接（上下文管理器）"""
        client = None
        try:
            client = self._available.get(timeout=timeout)
            yield client
        except Empty:
            logger.error("No available connections in pool")
            raise ConnectionError("Connection pool exhausted")
        finally:
            if client:
                self._available.put(client)

    def _heartbeat_loop(self):
        """心跳循环"""
        while self._running:
            time.sleep(self.config.heartbeat_interval)

            for client in self._connections:
                if not client.heartbeat():
                    logger.warning(f"Connection heartbeat failed, attempting reconnect")
                    with self._lock:
                        client.reconnect()

    def get_metrics(self) -> Dict[str, Any]:
        """获取连接池指标"""
        return {
            "pool_size": self.config.pool_size,
            "active_connections": len(self._connections),
            "available_connections": self._available.qsize(),
            "connections": [c.metrics.to_dict() for c in self._connections]
        }


# 全局单例
_default_pool: Optional[OpenDConnectionPool] = None


def get_default_pool(config: Optional[OpenDConfig] = None) -> OpenDConnectionPool:
    """获取默认连接池"""
    global _default_pool
    if _default_pool is None:
        if config is None:
            config = OpenDConfig(
                host=os.getenv("OPEND_HOST", "127.0.0.1"),
                port=int(os.getenv("OPEND_PORT", "11111")),
                trd_env=int(os.getenv("OPEND_TRD_ENV", "1")),
                password=os.getenv("OPEND_TRADE_PASSWORD")
            )
        _default_pool = OpenDConnectionPool(config)
    return _default_pool


def init_opend(config: Optional[OpenDConfig] = None) -> bool:
    """初始化 OpenD 连接"""
    pool = get_default_pool(config)
    return pool.initialize()


def shutdown_opend():
    """关闭 OpenD 连接"""
    global _default_pool
    if _default_pool:
        _default_pool.shutdown()
        _default_pool = None
