import asyncio

import pytest
from aiocache import MemcachedCache, RedisCache

from asyncio_toolkit.circuit_breaker.storage import MemoryStorage


@pytest.fixture(scope='session')
def loop():
    return asyncio.get_event_loop()


@pytest.fixture
def run_sync(loop):
    return loop.run_until_complete


@pytest.fixture
def memcached():
    return MemcachedCache(
        endpoint='127.0.0.1',
        port=11211,
        loop=asyncio.get_event_loop()
    )


@pytest.fixture
def redis(run_sync):
    return RedisCache(
        endpoint='127.0.0.1',
        port=6379
    )


@pytest.fixture
def memory():
    return MemoryStorage()
