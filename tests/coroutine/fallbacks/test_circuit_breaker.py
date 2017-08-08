import pytest
from werkzeug.contrib.cache import SimpleCache

from asyncio_toolkit.coroutine.fallbacks.circuit_breaker import CircuitBreaker

cache = SimpleCache()


class MyException(Exception):
    pass


def success_function():
    return True


def fail_function():
    raise ValueError()


class TestCircuitBreaker:

    def test_success_result(self):
        with CircuitBreaker(
            cache=cache,
            failure_cache_key='success',
            max_failures=1,
            max_failure_exception=None,
            catch_exceptions=None,
        ):
            success_function()

    def test_should_raise_error_when_max_failures_is_exceeded(self):
        with pytest.raises(MyException):
            with CircuitBreaker(
                cache=cache,
                failure_cache_key='fail',
                max_failures=0,
                max_failure_exception=MyException,
                catch_exceptions=(ValueError,),
            ):
                fail_function()

    def test_should_increase_fail_cache_count(self):
        failure_cache_key = 'fail_count'

        cache.set(failure_cache_key, 171)

        with pytest.raises(ValueError):
            with CircuitBreaker(
                cache=cache,
                failure_cache_key=failure_cache_key,
                max_failures=5000,
                max_failure_exception=MyException,
                catch_exceptions=(ValueError,),
            ):
                fail_function()

        assert cache.get(failure_cache_key) == 172

    def test_should_open_circuit_when_max_failures_exceeds(self):
        failure_cache_key = 'circuit'

        cache.set(failure_cache_key, 1)

        with pytest.raises(MyException):
            with CircuitBreaker(
                cache=cache,
                failure_cache_key=failure_cache_key,
                max_failures=2,
                max_failure_exception=MyException,
                catch_exceptions=(ValueError,),
            ) as circuit_breaker:
                fail_function()

            assert circuit_breaker.is_circuit_open

        assert cache.get(failure_cache_key) == 2

    def test_should_raise_exception_when_circuit_is_open(self):
        cache.set('circuit_circuit_open', True)

        with pytest.raises(MyException):
            with CircuitBreaker(
                cache=cache,
                failure_cache_key='circuit_open',
                max_failures=10,
                max_failure_exception=MyException,
                catch_exceptions=(ValueError,),
            ) as circuit_breaker:
                success_function()

            assert circuit_breaker.is_circuit_open

    def test_should_not_increment_fail_when_circuit_is_open(self):
        """
        It should not increment fail count over the max failures limit, when
        circuit breaker is open after a successful enter.
        """
        failure_cache_key = 'fail_count'
        max_failures = 10

        with pytest.raises(MyException):
            with CircuitBreaker(
                cache=cache,
                failure_cache_key=failure_cache_key,
                max_failures=max_failures,
                max_failure_exception=MyException,
                catch_exceptions=(ValueError,),
            ) as circuit_breaker:
                cache.set(failure_cache_key, max_failures)
                circuit_breaker.open_circuit()

                fail_function()

        assert cache.get(failure_cache_key) == max_failures
