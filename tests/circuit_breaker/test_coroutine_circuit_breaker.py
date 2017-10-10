import asyncio
import aioredis

import aiomcache
import pytest

from asyncio_toolkit.circuit_breaker.coroutine import circuit_breaker

from .helpers import MyException

max_failures = 10

failure_key = 'fail'


class TestCoroutineCircuitBreaker:

    @pytest.fixture
    def memcached(self):
        return aiomcache.Client(
            '127.0.0.1', 11211,
            loop=asyncio.get_event_loop()
        )

    @pytest.fixture
    def fail_example(self, memcached):

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

    def success_example(self, memcached):

        @circuit_breaker(
            storage=memcached,
            failure_key=failure_key,
            max_failures=max_failures,
            max_failure_exception=None,
            catch_exceptions=None,
        )
        @asyncio.coroutine
        def fn():
            return True

        return fn

    def _set_failure_count(self, stored, run_sync, count):
        run_sync(stored.flush_all())
        run_sync(stored.add(
            failure_key.encode('utf-8'),
            str(count).encode('utf-8'),
            60
        ))

    def _get_failure_count(self, stored, run_sync, key):
        return int(run_sync(stored.get(key.encode('utf-8'))))

    @pytest.mark.parametrize('store_fixture', 
        [
            ('memcached'),
        ]
    )
    def test_error_is_raised_when_max_failures_exceeds_max_value(
        self,
        request,
        store_fixture,
        run_sync,
        fail_example
    ):
        store = request.getfuncargvalue(store_fixture)
        self._set_failure_count(store, run_sync, max_failures + 1)
        with pytest.raises(MyException):
            run_sync(fail_example())

    @pytest.mark.parametrize('store_fixture', 
        [
            ('memcached'),
        ]
    )
    def test_failure_increases_count_on_storage(
        self,
        request,
        store_fixture,
        run_sync,
        fail_example
    ):
        store = request.getfuncargvalue(store_fixture)
        self._set_failure_count(store, run_sync, max_failures - 1)

        with pytest.raises(MyException):
            run_sync(fail_example())

        count = self._get_failure_count(store, run_sync, failure_key)
        assert count == max_failures

    @pytest.mark.parametrize('store_fixture', 
        [
            ('memcached'),
        ]
    )
    def test_should_not_increment_fail_when_circuit_is_open(
        self,
        request,
        store_fixture,
        run_sync,
        fail_example
    ):
        store = request.getfuncargvalue(store_fixture)
        self._set_failure_count(store, run_sync, 999)
        run_sync(store.set(
            'circuit_{}'.format(failure_key).encode('utf-8'),
            b'{"py/bytes": "=00"}'
        ))

        with pytest.raises(MyException):
            run_sync(fail_example())

        count = self._get_failure_count(store, run_sync, failure_key)
        assert count == 999
