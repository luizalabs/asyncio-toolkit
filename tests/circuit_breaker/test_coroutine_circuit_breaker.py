import asyncio
import aioredis

import aiomcache
import pytest

from asyncio_toolkit.circuit_breaker.coroutine import circuit_breaker

from .helpers import MyException

max_failures = 10

failure_key = 'fail'


def set_failure_count_memcached(request, count):
    store = request.getfuncargvalue('memcached')
    run_sync = request.getfuncargvalue('run_sync')
    key = failure_key.encode('utf-8')
    run_sync(store.delete(key))
    run_sync(store.add(
        key,
        str(count).encode('utf-8'),
        60
    ))


def set_failure_count_redis(request, count):
    store = request.getfuncargvalue('redis')
    run_sync = request.getfuncargvalue('run_sync')
    key = failure_key.encode('utf-8')
    run_sync(store.delete(key))
    run_sync(store.set(
        key,
        count,
        expire=60
    ))


def set_failure_count_redis_pool(request, count):
    store = request.getfuncargvalue('redis')
    run_sync = request.getfuncargvalue('run_sync')
    key = failure_key.encode('utf-8')

    with run_sync(store) as redis:
        run_sync(redis.delete(key))
        run_sync(redis.set(
            key,
            count,
            expire=60
        ))


def get_failure_count_memcached(request, run_sync):
    key = failure_key.encode('utf-8')
    store = request.getfuncargvalue('memcached')
    return int(run_sync(stored.get(key)))


def get_failure_count_redis(request, run_sync):
    key = failure_key.encode('utf-8')
    store = request.getfuncargvalue('redis')
    return int(run_sync(stored.get(key)))


def get_failure_count_redis_pool(request, run_sync):
    key = failure_key.encode('utf-8')
    store = request.getfuncargvalue('redis_pool')
    with run_sync(store) as redis:
        return int(run_sync(redis.get(key)))


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
        'store_fixture,fail_example_fixture,set_failure_count',
        [
            ('memcached', 'fail_example_memcached', set_failure_count_memcached),
            ('redis', 'fail_example_redis', set_failure_count_redis),
            ('redis_pool', 'fail_example_redis_pool', set_failure_count_redis_pool),
        ]
    )
    def test_error_is_raised_when_max_failures_exceeds_max_value(
        self,
        request,
        store_fixture,
        fail_example_fixture,
        set_failure_count,
        run_sync
    ):
        store = request.getfuncargvalue(store_fixture)
        fail_example = request.getfuncargvalue(fail_example_fixture)
        set_failure_count(request, max_failures + 1)
        with pytest.raises(MyException):
            run_sync(fail_example())

    @pytest.mark.parametrize(
        'store_fixture,fail_example_fixture,set_failure_count,get_failure_count',
        [
            ('memcached', 'fail_example_memcached',
             set_failure_count_memcached, get_failure_count_memcached),
            
            ('redis', 'fail_example_redis',
             set_failure_count_redis, get_failure_count_redis),
            
            ('redis_pool', 'fail_example_redis_pool',
             set_failure_count_redis_pool, get_failure_count_redis_pool),
        ]
    )
    def test_failure_increases_count_on_storage(
        self,
        request,
        store_fixture,
        fail_example_fixture,
        set_failure_count,
        get_failure_count,
        run_sync
    ):
        store = request.getfuncargvalue(store_fixture)
        fail_example = request.getfuncargvalue(fail_example_fixture)
        set_failure_count(request, max_failures - 1)

        with pytest.raises(MyException):
            run_sync(fail_example())

        count = get_failure_count(request, run_sync)
        assert count == max_failures

    @pytest.mark.parametrize(
        'store_fixture,fail_example_fixture,set_failure_count,get_failure_count',
        [
            ('memcached', 'fail_example_memcached',
             set_failure_count_memcached, get_failure_count_memcached),
            
            ('redis', 'fail_example_redis',
             set_failure_count_redis, get_failure_count_redis),
            
            ('redis_pool', 'fail_example_redis_pool',
             set_failure_count_redis_pool, get_failure_count_redis_pool),
        ]
    )
    def test_should_not_increment_fail_when_circuit_is_open(
        self,
        request,
        store_fixture,
        fail_example_fixture,
        set_failure_count,
        get_failure_count,
        run_sync
    ):
        store = request.getfuncargvalue(store_fixture)
        fail_example = request.getfuncargvalue(fail_example_fixture)
        set_failure_count(request, 999)
        run_sync(store.set(
            'circuit_{}'.format(failure_key).encode('utf-8'),
            b'{"py/bytes": "=00"}'
        ))

        with pytest.raises(MyException):
            run_sync(fail_example())

        count = get_failure_count(store, run_sync, failure_key)
        assert count == 999
