import asyncio

import pytest

from tests.factory import (
    create_memcached_instance,
    create_memory_instance,
    create_redis_instance
)


@pytest.fixture(scope='session')
def loop():
    return asyncio.get_event_loop()


@pytest.fixture
def run_sync(loop):
    return loop.run_until_complete


@pytest.fixture
def memcached():
    return create_memcached_instance()


@pytest.fixture
def redis(run_sync):
    return create_redis_instance()


@pytest.fixture
def memory():
    return create_memory_instance()
