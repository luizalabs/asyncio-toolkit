import pytest
from werkzeug.contrib.cache import SimpleCache

from asyncio_toolkit.circuit_breaker.context_manager import (
    CircuitBreaker as SimpleCircuitBreaker
)

from .helpers import MyException

simple_storage = SimpleCache()


def success_function():
    return True


def fail_function():
    raise ValueError()


class TestBaseCircuitBreaker:

    def test_success_result(self):
        with SimpleCircuitBreaker(
            storage=simple_storage,
            failure_key='success',
            max_failures=1,
            max_failure_exception=None,
            catch_exceptions=None,
        ):
            success_function()

    def test_should_raise_error_when_max_failures_is_exceeded(self):
        with pytest.raises(MyException):
            with SimpleCircuitBreaker(
                storage=simple_storage,
                failure_key='fail',
                max_failures=0,
                max_failure_exception=MyException,
                catch_exceptions=(ValueError,),
            ):
                fail_function()

    def test_should_increase_fail_storage_count(self):
        failure_key = 'fail_count'

        simple_storage.set(failure_key, 171)

        with pytest.raises(ValueError):
            with SimpleCircuitBreaker(
                storage=simple_storage,
                failure_key=failure_key,
                max_failures=5000,
                max_failure_exception=MyException,
                catch_exceptions=(ValueError,),
            ):
                fail_function()

        assert simple_storage.get(failure_key) == 172

    def test_should_open_circuit_when_max_failures_exceeds(self):
        failure_key = 'circuit'

        simple_storage.set(failure_key, 1)

        with pytest.raises(MyException):
            with SimpleCircuitBreaker(
                storage=simple_storage,
                failure_key=failure_key,
                max_failures=2,
                max_failure_exception=MyException,
                catch_exceptions=(ValueError,),
            ) as circuit_breaker:
                fail_function()

            assert circuit_breaker.is_circuit_open

        assert simple_storage.get(failure_key) == 2

    def test_should_raise_exception_when_circuit_is_open(self):
        simple_storage.set('circuit_failure_key', True)

        with pytest.raises(MyException):
            circuit_breaker = SimpleCircuitBreaker(
                storage=simple_storage,
                failure_key='failure_key',
                max_failures=10,
                max_failure_exception=MyException,
                catch_exceptions=(ValueError,),
            )

            with circuit_breaker:
                success_function()

            assert circuit_breaker.is_circuit_open

    def test_should_not_increment_fail_when_circuit_is_open(self):
        """
        It should not increment fail count over the max failures limit, when
        circuit breaker is open after a successful enter.
        """
        failure_key = 'failure_count'
        max_failures = 10

        simple_storage.set(failure_key, max_failures)

        with pytest.raises(MyException):
            with SimpleCircuitBreaker(
                storage=simple_storage,
                failure_key=failure_key,
                max_failures=10,
                max_failure_exception=MyException,
                catch_exceptions=(ValueError,),
            ) as circuit_breaker:
                circuit_breaker.open_circuit()
                fail_function()

        assert simple_storage.get(failure_key) == max_failures
