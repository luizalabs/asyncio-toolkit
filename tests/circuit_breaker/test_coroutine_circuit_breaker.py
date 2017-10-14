import asyncio

import aiomcache
import aioredis
import pytest

from asyncio_toolkit.circuit_breaker.async_await import (
    circuit_breaker as async_circuit_breaker
)
from asyncio_toolkit.circuit_breaker.coroutine import circuit_breaker

from .helpers import MyException

max_failures = 10

failure_key = 'fail'


def set_failure_count_memcached(request, count):
    storage = request.getfuncargvalue('memcached')
    run_sync = request.getfuncargvalue('run_sync')
    key = failure_key.encode('utf-8')
    run_sync(storage.delete(key))
    run_sync(storage.add(
        key,
        str(count).encode('utf-8'),
        60
    ))


def set_failure_count_redis(request, count):
    storage = request.getfuncargvalue('redis')
    run_sync = request.getfuncargvalue('run_sync')
    key = failure_key.encode('utf-8')
    run_sync(storage.delete(key))
    run_sync(storage.set(
        key,
        count,
        expire=60
    ))


def get_failure_count_memcached(request, run_sync):
    key = failure_key.encode('utf-8')
    storage = request.getfuncargvalue('memcached')
    return int(run_sync(storage.get(key)))


def get_failure_count_redis(request, run_sync):
    key = failure_key.encode('utf-8')
    storage = request.getfuncargvalue('redis')
    return int(run_sync(storage.get(key)))


class TestCoroutineCircuitBreaker:

    @pytest.fixture
    def memcached(self):
        return aiomcache.Client(
            '127.0.0.1', 11211,
            loop=asyncio.get_event_loop()
        )

    @pytest.fixture
    def redis(self, run_sync):
        return run_sync(
            aioredis.create_redis(('127.0.0.1', 6379))
        )

    @pytest.fixture
    def redis_pool(self, run_sync):
        return run_sync(
            aioredis.create_pool(
                ('127.0.0.1', 6379), minsize=5, maxsize=10
            )
        )

    @pytest.fixture
    def flush_cache(self, memcached, redis, run_sync):
        run_sync(redis.flushall())
        run_sync(memcached.flush_all())

    @pytest.fixture
    def open_circuit(self, memcached, redis, run_sync):
        key = 'circuit_{}'.format(failure_key).encode('utf-8')
        run_sync(memcached.set(key, bytes(1)))
        run_sync(redis.set(key, 1))

    @pytest.fixture
    def fail_example_async(self, memcached):

        @async_circuit_breaker(
            storage=memcached,
            failure_key=failure_key,
            max_failures=max_failures,
            max_failure_exception=MyException,
            max_failure_timeout=10,
            circuit_timeout=10,
            catch_exceptions=(ValueError,),
        )
        @asyncio.coroutine
        def fn():
            raise ValueError()

        return fn

    @pytest.fixture
    def fail_example_memcached(self, memcached):

        @circuit_breaker(
            storage=memcached,
            failure_key=failure_key,
            max_failures=max_failures,
            max_failure_exception=MyException,
            max_failure_timeout=10,
            circuit_timeout=10,
            catch_exceptions=(ValueError,),
        )
        @asyncio.coroutine
        def fn():
            raise ValueError()

        return fn

    @pytest.fixture
    def fail_example_redis(self, redis):

        @circuit_breaker(
            storage=redis,
            failure_key=failure_key,
            max_failures=max_failures,
            max_failure_exception=MyException,
            max_failure_timeout=10,
            circuit_timeout=10,
            catch_exceptions=(ValueError,),
        )
        @asyncio.coroutine
        def fn():
            raise ValueError()

        return fn

    @pytest.fixture
    def fail_example_redis_pool(self, redis_pool):

        @circuit_breaker(
            storage=redis_pool,
            failure_key=failure_key,
            max_failures=max_failures,
            max_failure_exception=MyException,
            max_failure_timeout=10,
            circuit_timeout=10,
            catch_exceptions=(ValueError,),
        )
        @asyncio.coroutine
        def fn():
            raise ValueError()

        return fn

    @pytest.mark.parametrize(
        'fail_example_fixture,set_failure_count',
        [
            ('fail_example_async', set_failure_count_memcached),
            ('fail_example_memcached', set_failure_count_memcached),
            ('fail_example_redis', set_failure_count_redis),
            ('fail_example_redis_pool', set_failure_count_redis),
        ]
    )
    def test_error_is_raised_when_max_failures_exceeds_max_value(
        self,
        request,
        fail_example_fixture,
        set_failure_count,
        run_sync,
        flush_cache
    ):
        fail_example = request.getfuncargvalue(fail_example_fixture)
        set_failure_count(request, max_failures + 1)
        with pytest.raises(MyException):
            run_sync(fail_example())

    @pytest.mark.parametrize(
        'fail_example_fixture,set_failure_count,get_failure_count',
        [
            ('fail_example_async',
             set_failure_count_memcached, get_failure_count_memcached),

            ('fail_example_memcached',
             set_failure_count_memcached, get_failure_count_memcached),

            ('fail_example_redis',
             set_failure_count_redis, get_failure_count_redis),

            ('fail_example_redis_pool',
             set_failure_count_redis, get_failure_count_redis),
        ]
    )
    def test_failure_increases_count_on_storage(
        self,
        request,
        fail_example_fixture,
        set_failure_count,
        get_failure_count,
        run_sync,
        flush_cache
    ):
        fail_example = request.getfuncargvalue(fail_example_fixture)

        set_failure_count(request, max_failures - 1)
        count = get_failure_count(request, run_sync)

        with pytest.raises(MyException):
            run_sync(fail_example())

        count = get_failure_count(request, run_sync)
        assert count == max_failures

    @pytest.mark.parametrize(
        'fail_example_fixture,set_failure_count,get_failure_count',
        [
            ('fail_example_memcached',
             set_failure_count_memcached, get_failure_count_memcached),

            ('fail_example_async',
             set_failure_count_memcached, get_failure_count_memcached),

            ('fail_example_redis',
             set_failure_count_redis, get_failure_count_redis),

            ('fail_example_redis_pool',
             set_failure_count_redis, get_failure_count_redis),
        ]
    )
    def test_should_not_increment_fail_when_circuit_is_open(
        self,
        request,
        fail_example_fixture,
        set_failure_count,
        get_failure_count,
        run_sync,
        flush_cache,
        open_circuit,
    ):
        fail_example = request.getfuncargvalue(fail_example_fixture)
        set_failure_count(request, 999)

        with pytest.raises(MyException):
            run_sync(fail_example())

        count = get_failure_count(request, run_sync)
        assert count == 999
