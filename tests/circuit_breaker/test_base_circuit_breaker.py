from unittest import mock

import pytest

from asyncio_toolkit.circuit_breaker.context_manager import (
    CircuitBreaker as SimpleCircuitBreaker
)

from .helpers import MyException


def success_function():
    return True


def fail_function():
    raise ValueError()


class TestBaseCircuitBreaker:

    @pytest.fixture
    def default_timeout(self):
        return 60

    def test_success_result(self, memory):
        with SimpleCircuitBreaker(
            storage=memory,
            failure_key='success',
            max_failures=1,
            max_failure_exception=None,
            catch_exceptions=None,
        ):
            success_function()

    def test_should_raise_error_when_max_failures_is_exceeded(self, memory):
        with pytest.raises(MyException):
            with SimpleCircuitBreaker(
                storage=memory,
                failure_key='fail',
                max_failures=0,
                max_failure_exception=MyException,
                catch_exceptions=(ValueError,),
            ):
                fail_function()

    def test_should_increase_fail_storage_count(self, memory, default_timeout):
        failure_key = 'fail_count'

        memory.set(failure_key, 171, default_timeout)

        with pytest.raises(ValueError):
            with SimpleCircuitBreaker(
                storage=memory,
                failure_key=failure_key,
                max_failures=5000,
                max_failure_exception=MyException,
                catch_exceptions=(ValueError,),
            ):
                fail_function()

        assert memory.get(failure_key) == 172

    def test_should_set_failure_key_timeout_on_first_increase_count(
        self,
        memory
    ):
        failure_key = 'fail_count'
        max_failure_timeout = 4

        memory.set(failure_key, 0, 10)
        memory.expire = mock.Mock()
        with pytest.raises(ValueError):
            with SimpleCircuitBreaker(
                storage=memory,
                failure_key=failure_key,
                max_failures=5000,
                max_failure_exception=MyException,
                max_failure_timeout=max_failure_timeout,
                catch_exceptions=(ValueError,),
            ):
                fail_function()

        assert memory.get(failure_key) == 1
        memory.expire.assert_called_once_with(
            failure_key,
            max_failure_timeout
        )

    def test_should_not_set_failure_key_timeout_after_first_increase_count(
        self,
        memory
    ):
        failure_key = 'fail_count'

        memory.set(failure_key, 1, 10)
        memory.expire = mock.Mock()
        with pytest.raises(ValueError):
            with SimpleCircuitBreaker(
                storage=memory,
                failure_key=failure_key,
                max_failures=5000,
                max_failure_exception=MyException,
                max_failure_timeout=4,
                catch_exceptions=(ValueError,),
            ):
                fail_function()

        assert memory.get(failure_key) == 2
        assert not memory.expire.called

    def test_should_open_circuit_when_max_failures_exceeds(self, memory, default_timeout):
        failure_key = 'circuit'

        memory.set(failure_key, 1, default_timeout)

        with pytest.raises(MyException):
            with SimpleCircuitBreaker(
                storage=memory,
                failure_key=failure_key,
                max_failures=2,
                max_failure_exception=MyException,
                catch_exceptions=(ValueError,),
            ) as circuit_breaker:
                fail_function()

            assert circuit_breaker.is_circuit_open

        assert memory.get(failure_key) == 2

    def test_should_raise_exception_when_circuit_is_open(self, memory, default_timeout):
        memory.set('circuit_failure_key', True, default_timeout)

        with pytest.raises(MyException):
            circuit_breaker = SimpleCircuitBreaker(
                storage=memory,
                failure_key='failure_key',
                max_failures=10,
                max_failure_exception=MyException,
                catch_exceptions=(ValueError,),
            )

            with circuit_breaker:
                success_function()

            assert circuit_breaker.is_circuit_open

    def test_should_not_increment_fail_when_circuit_is_open(self, memory, default_timeout):
        """
        It should not increment fail count over the max failures limit, when
        circuit breaker is open after a successful enter.
        """
        failure_key = 'failure_count'
        max_failures = 10

        memory.set(failure_key, max_failures, default_timeout)

        with pytest.raises(MyException):
            with SimpleCircuitBreaker(
                storage=memory,
                failure_key=failure_key,
                max_failures=10,
                max_failure_exception=MyException,
                catch_exceptions=(ValueError,),
            ) as circuit_breaker:
                circuit_breaker.open_circuit()
                fail_function()

        assert memory.get(failure_key) == max_failures
