import asyncio

import aiomcache
import pytest

from asyncio_toolkit.circuit_breaker.coroutine import circuit_breaker

from .helpers import MyException

max_failures = 10

failure_key = 'fail'

simple_storage = aiomcache.Client(
    '127.0.0.1', 11211,
    loop=asyncio.get_event_loop()
)


class Clazz:

    @classmethod
    @circuit_breaker(
        storage=simple_storage,
        failure_key=failure_key,
        max_failures=max_failures,
        max_failure_exception=None,
        catch_exceptions=None,
    )
    @asyncio.coroutine
    def success_example(cls):
        return True

    @classmethod
    @circuit_breaker(
        storage=simple_storage,
        failure_key=failure_key,
        max_failures=max_failures,
        max_failure_exception=MyException,
        max_failure_timeout=10,
        circuit_timeout=10,
        catch_exceptions=(ValueError,),
    )
    @asyncio.coroutine
    def fail_example(cls):
        raise ValueError()


class TestCoroutineCircuitBreaker:

    def _set_failure_count(self, run_sync, count):
        run_sync(simple_storage.flush_all())
        run_sync(simple_storage.add(
            failure_key.encode('utf-8'),
            str(count).encode('utf-8'),
            60
        ))

    def _get_failure_count(self, run_sync, key):
        return int(run_sync(simple_storage.get(key.encode('utf-8'))))

    def test_error_is_raised_when_max_failures_exceeds_max_value(
        self, run_sync
    ):
        self._set_failure_count(run_sync, max_failures + 1)
        with pytest.raises(MyException):
            run_sync(Clazz.fail_example())

    def test_failure_increases_count_on_storage(self, run_sync):
        self._set_failure_count(run_sync, max_failures - 1)

        with pytest.raises(MyException):
            run_sync(Clazz.fail_example())

        count = self._get_failure_count(run_sync, failure_key)
        assert count == max_failures

    def test_should_not_increment_fail_when_circuit_is_open(self, run_sync):
        self._set_failure_count(run_sync, 999)
        run_sync(simple_storage.set(
            'circuit_{}'.format(failure_key).encode('utf-8'),
            b'{"py/bytes": "=00"}'
        ))

        with pytest.raises(MyException):
            run_sync(Clazz.fail_example())

        count = self._get_failure_count(run_sync, failure_key)
        assert count == 999
