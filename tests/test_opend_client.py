# -*- coding: utf-8 -*-
"""
OpenD 客户端单元测试
"""

import pytest
import asyncio
import threading
import time
from unittest.mock import Mock, patch, MagicMock

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from futu.opend_client import (
    OpenDClient, OpenDConnectionPool, OpenDConfig,
    ConnectionState, ConnectionMetrics,
    init_opend, shutdown_opend, get_default_pool
)


class TestOpenDConfig:
    """OpenD 配置测试"""

    def test_default_config(self):
        """测试默认配置"""
        config = OpenDConfig()

        assert config.host == "127.0.0.1"
        assert config.port == 11111
        assert config.trd_env == 1  # 模拟环境
        assert config.market == "US"
        assert config.pool_size == 3
        assert config.max_retries == 5
        assert config.heartbeat_interval == 30.0

    def test_custom_config(self):
        """测试自定义配置"""
        config = OpenDConfig(
            host="192.168.1.100",
            port=22222,
            trd_env=0,
            market="HK",
            pool_size=5
        )

        assert config.host == "192.168.1.100"
        assert config.port == 22222
        assert config.trd_env == 0  # 真实环境
        assert config.market == "HK"
        assert config.pool_size == 5


class TestConnectionMetrics:
    """连接指标测试"""

    def test_record_latency(self):
        """测试延迟记录"""
        metrics = ConnectionMetrics()

        metrics.record_latency(10.5)
        metrics.record_latency(20.3)
        metrics.record_latency(15.2)

        assert len(metrics.latency_samples) == 3
        assert abs(metrics.average_latency_ms - 15.33) < 0.1

    def test_latency_window(self):
        """测试延迟窗口限制"""
        metrics = ConnectionMetrics()

        for i in range(1100):
            metrics.record_latency(float(i))

        assert len(metrics.latency_samples) == 1000

    def test_to_dict(self):
        """测试转换为字典"""
        metrics = ConnectionMetrics()
        metrics.total_requests = 100
        metrics.successful_requests = 95
        metrics.failed_requests = 5

        result = metrics.to_dict()

        assert result["total_requests"] == 100
        assert result["success_rate"] == 0.95
        assert result["reconnect_count"] == 0


class TestOpenDClient:
    """OpenD 客户端测试"""

    def test_initial_state(self):
        """测试初始状态"""
        config = OpenDConfig()
        client = OpenDClient(config)

        assert client.state == ConnectionState.DISCONNECTED
        assert client.quote_ctx is None
        assert client.trade_ctx is None
        assert not client.is_connected

    def test_connect_mock(self):
        """测试连接（Mock 模式）"""
        config = OpenDConfig()
        client = OpenDClient(config)

        # 在没有 futu-api 的情况下应该使用 mock 连接
        result = client.connect()

        assert result == True
        assert client.state == ConnectionState.CONNECTED
        assert client.is_connected

    def test_disconnect(self):
        """测试断开连接"""
        config = OpenDConfig()
        client = OpenDClient(config)

        client.connect()
        client.disconnect()

        assert client.state == ConnectionState.DISCONNECTED
        assert not client.is_connected

    def test_reconnect(self):
        """测试重连"""
        config = OpenDConfig(max_retries=2, retry_delay=0.1)
        client = OpenDClient(config)

        result = client.reconnect()

        assert result == True
        assert client.metrics.reconnect_count == 1

    def test_callback_registration(self):
        """测试回调注册"""
        config = OpenDConfig()
        client = OpenDClient(config)

        callback_called = [False]

        def on_connect():
            callback_called[0] = True

        client.register_callback("on_connect", on_connect)
        client.connect()

        assert callback_called[0] == True


class TestOpenDConnectionPool:
    """连接池测试"""

    def test_pool_initialization(self):
        """测试连接池初始化"""
        config = OpenDConfig(pool_size=2)
        pool = OpenDConnectionPool(config)

        result = pool.initialize()

        assert result == True
        assert len(pool._connections) == 2

        pool.shutdown()

    def test_get_connection(self):
        """测试获取连接"""
        config = OpenDConfig(pool_size=2)
        pool = OpenDConnectionPool(config)
        pool.initialize()

        with pool.get_connection() as client:
            assert client is not None
            assert client.is_connected

        pool.shutdown()

    def test_connection_exhaustion(self):
        """测试连接耗尽"""
        config = OpenDConfig(pool_size=1)
        pool = OpenDConnectionPool(config)
        pool.initialize()

        with pool.get_connection() as client1:
            # 尝试获取第二个连接应该超时
            with pytest.raises(ConnectionError):
                with pool.get_connection(timeout=0.1) as client2:
                    pass

        pool.shutdown()

    def test_get_metrics(self):
        """测试获取指标"""
        config = OpenDConfig(pool_size=2)
        pool = OpenDConnectionPool(config)
        pool.initialize()

        metrics = pool.get_metrics()

        assert metrics["pool_size"] == 2
        assert metrics["active_connections"] == 2
        assert len(metrics["connections"]) == 2

        pool.shutdown()


class TestGlobalFunctions:
    """全局函数测试"""

    def test_init_and_shutdown(self):
        """测试初始化和关闭"""
        config = OpenDConfig(pool_size=1)

        result = init_opend(config)
        assert result == True

        pool = get_default_pool()
        assert pool is not None

        shutdown_opend()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
