import asyncio

import aiomcache
import aioredis
import pytest
from werkzeug.contrib.cache import SimpleCache


@pytest.fixture(scope='session')
def loop():
    return asyncio.get_event_loop()


@pytest.fixture
def run_sync(loop):
    return loop.run_until_complete


@pytest.fixture
def memcached():
    return aiomcache.Client(
        '127.0.0.1', 11211,
        loop=asyncio.get_event_loop()
    )


@pytest.fixture
def redis(run_sync):
    return run_sync(
        aioredis.create_redis(('127.0.0.1', 6379))
    )


@pytest.fixture
def redis_pool(run_sync):
    return run_sync(
        aioredis.create_pool(
            ('127.0.0.1', 6379), minsize=5, maxsize=10
        )
    )


@pytest.fixture
def simple_cache():
    return SimpleCache()
