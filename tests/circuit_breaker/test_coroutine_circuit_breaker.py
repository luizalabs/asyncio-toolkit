import asyncio
from unittest import mock

import pytest

from asyncio_toolkit.circuit_breaker.async_await import (
    circuit_breaker as async_circuit_breaker
)
from asyncio_toolkit.circuit_breaker.coroutine import circuit_breaker

from .helpers import MyException

max_failures = 10
max_failure_timeout = 8
failure_key = 'fail'


def set_failure_count_memcached(request, count):
    storage = request.getfuncargvalue('memcached')
    run_sync = request.getfuncargvalue('run_sync')
    key = failure_key
    run_sync(storage.delete(key))
    run_sync(storage.add(
        key,
        count,
        60
    ))


def set_failure_count_redis(request, count):
    storage = request.getfuncargvalue('redis')
    run_sync = request.getfuncargvalue('run_sync')
    key = failure_key
    run_sync(storage.delete(key))
    run_sync(storage.set(
        key,
        count,
        ttl=60
    ))


def get_failure_count_memcached(request, run_sync):
    key = failure_key
    storage = request.getfuncargvalue('memcached')
    return int(run_sync(storage.get(key)) or 0)


def get_failure_count_redis(request, run_sync):
    key = failure_key
    storage = request.getfuncargvalue('redis')
    return int(run_sync(storage.get(key)) or 0)


class TestCoroutineCircuitBreaker:

    @pytest.fixture
    def flush_cache(self, memcached, redis, run_sync):
        run_sync(redis.clear())
        run_sync(memcached.clear())

    @pytest.fixture
    def open_circuit(self, memcached, redis, run_sync):
        key = 'circuit_{}'.format(failure_key)
        run_sync(memcached.set(key, 1))
        run_sync(redis.set(key, 1))

    @pytest.fixture
    def fail_example_async(self, memcached):

        @async_circuit_breaker(
            storage=memcached,
            failure_key=failure_key,
            max_failures=max_failures,
            max_failure_exception=MyException,
            max_failure_timeout=max_failure_timeout,
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
            max_failure_timeout=max_failure_timeout,
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
            max_failure_timeout=max_failure_timeout,
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
            (
                'fail_example_async',
                set_failure_count_memcached,
                get_failure_count_memcached
            ),
            (
                'fail_example_memcached',
                set_failure_count_memcached,
                get_failure_count_memcached
            ),
            (
                'fail_example_redis',
                set_failure_count_redis,
                get_failure_count_redis
            ),
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
        assert count == 0

    @pytest.mark.parametrize(
        'fail_example_fixture,set_failure_count,'
        'get_failure_count,storage_type',
        [
            (
                'fail_example_async',
                set_failure_count_memcached,
                get_failure_count_memcached,
                'memcached'
            ),
            (
                'fail_example_memcached',
                set_failure_count_memcached,
                get_failure_count_memcached,
                'memcached'
            ),
            (
                'fail_example_redis',
                set_failure_count_redis,
                get_failure_count_redis,
                'redis'
            ),
        ]
    )
    def test_should_set_failure_key_timeout_on_first_increase_count(
        self,
        request,
        fail_example_fixture,
        set_failure_count,
        get_failure_count,
        storage_type,
        run_sync,
        flush_cache
    ):
        fail_example = request.getfuncargvalue(fail_example_fixture)
        storage = request.getfuncargvalue(storage_type)

        expire_mock = mock.Mock()
        expire_mock.side_effect = asyncio.coroutine(
            mock.Mock(name='CoroutineResult')
        )
        storage.expire = expire_mock

        set_failure_count(request, 0)
        with pytest.raises(ValueError):
            run_sync(fail_example())

        expire_mock.assert_called_once_with(
            failure_key,
            max_failure_timeout
        )

    @pytest.mark.parametrize(
        'fail_example_fixture,set_failure_count,'
        'get_failure_count,storage_type',
        [
            (
                'fail_example_async',
                set_failure_count_memcached,
                get_failure_count_memcached,
                'memcached'
            ),
            (
                'fail_example_memcached',
                set_failure_count_memcached,
                get_failure_count_memcached,
                'memcached'
            ),
            (
                'fail_example_redis',
                set_failure_count_redis,
                get_failure_count_redis,
                'redis'
            ),
        ]
    )
    def test_should_not_set_failure_key_timeout_after_first_increase_count(
        self,
        request,
        fail_example_fixture,
        set_failure_count,
        get_failure_count,
        storage_type,
        run_sync,
        flush_cache
    ):
        fail_example = request.getfuncargvalue(fail_example_fixture)
        storage = request.getfuncargvalue(storage_type)

        expire_mock = mock.Mock()
        expire_mock.side_effect = asyncio.coroutine(
            mock.Mock(name='CoroutineResult')
        )
        storage.expire = expire_mock

        set_failure_count(request, 1)
        with pytest.raises(ValueError):
            run_sync(fail_example())

        assert not expire_mock.called

    @pytest.mark.parametrize(
        'fail_example_fixture,set_failure_count,get_failure_count',
        [
            (
                'fail_example_memcached',
                set_failure_count_memcached,
                get_failure_count_memcached
            ),
            (
                'fail_example_async',
                set_failure_count_memcached,
                get_failure_count_memcached
            ),
            (
                'fail_example_redis',
                set_failure_count_redis,
                get_failure_count_redis
            ),
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

    @pytest.mark.parametrize(
        'fail_example_fixture,set_failure_count',
        [
            ('fail_example_async', set_failure_count_memcached),
            ('fail_example_memcached', set_failure_count_memcached),
            ('fail_example_redis', set_failure_count_redis),
        ]
    )
    def test_catched_error_is_raised_when_max_failures_are_not_exceeded(
        self,
        request,
        fail_example_fixture,
        set_failure_count,
        run_sync,
        flush_cache
    ):
        fail_example = request.getfuncargvalue(fail_example_fixture)
        with pytest.raises(ValueError):
            run_sync(fail_example())
