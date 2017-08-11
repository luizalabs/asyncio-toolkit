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
    def success_function(cls):
        return True

    @classmethod
    @circuit_breaker(
        storage=simple_storage,
        failure_key=failure_key,
        max_failures=max_failures,
        max_failure_exception=MyException,
        catch_exceptions=(ValueError,),
    )
    @asyncio.coroutine
    def fail_function(cls):
        raise ValueError()


class TestCoroutineCircuitBreaker:

    @pytest.mark.async
    @asyncio.coroutine
    def test_success_result(self):
        yield from Clazz.success_function()

    @pytest.mark.async
    @asyncio.coroutine
    def test_should_raise_error_when_max_failures_is_exceeded(self):
        with pytest.raises(MyException):
            yield from Clazz.fail_function()

    @pytest.mark.async
    @asyncio.coroutine
    def test_should_increase_fail_storage_count(self):
        yield from simple_storage.set(failure_key, 171)

        with pytest.raises(ValueError):
            yield from Clazz.fail_function()

        count = yield from simple_storage.get(failure_key)
        assert count == 172

    @pytest.mark.async
    @asyncio.coroutine
    def test_should_open_circuit_when_max_failures_exceeds(self):
        yield from simple_storage.set(failure_key, 1)

        with pytest.raises(MyException):
            yield from Clazz.fail_function()

            assert circuit_breaker.is_circuit_open

        assert (yield from simple_storage.get(failure_key)) == 2

    @pytest.mark.async
    @asyncio.coroutine
    def test_should_raise_exception_when_circuit_is_open(self):
        yield from simple_storage.set('circuit_failure_key', True)

        with pytest.raises(MyException):
            yield from Clazz.success_function()

            assert circuit_breaker.is_circuit_open

    @pytest.mark.async
    @asyncio.coroutine
    def test_should_not_increment_fail_when_circuit_is_open(self):
        """
        It should not increment fail count over the max failures limit, when
        circuit breaker is open after a successful enter.
        """
        max_failures = 10

        yield from simple_storage.set(failure_key, max_failures)

        with pytest.raises(MyException):
            circuit_breaker.open_circuit()
            yield from Clazz.fail_function()

        assert (yield from simple_storage.get(failure_key)) == max_failures
