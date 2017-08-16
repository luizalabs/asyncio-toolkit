import abc
import logging

logger = logging.getLogger(__name__)


class BaseCircuitBreaker(metaclass=abc.ABCMeta):
    """
    This class provides the basic logics to make the circuit breaker
    mechanism work as expected. Every logic must be implemented here,
    the other modules inside this package are strongly dependent on
    which kind of asynchronous model your
    code is running with (async/await or coroutines).
    """

    def __init__(
        self,
        storage,
        failure_key,
        max_failures,
        max_failure_exception,
        max_failure_timeout=None,
        circuit_timeout=None,
        catch_exceptions=None
    ):
        self.storage = storage
        self.failure_key = failure_key
        self.max_failure_timeout = max_failure_timeout
        self.circuit_timeout = circuit_timeout
        self.circuit_key = 'circuit_{}'.format(failure_key)
        self.max_failure_exception = max_failure_exception
        self.catch_exceptions = catch_exceptions or (Exception,)
        self.max_failures = max_failures

    @abc.abstractmethod
    def increment(self):
        """
        This method demands that the implementation is responsible for
        getting a storage key from the storage engine.
        """

    @property
    @abc.abstractmethod
    def is_circuit_open(self):
        """
        This method must implement a call to the storage engine in order
        to retrieve the current circuit state, based on this instance's key.
        """

    @abc.abstractmethod
    def open_circuit(self):
        """
        This method must "open the circuit" by setting this instance's key
        on the storage engine, and also, setting a TTL to it.
        """

    def _is_catchable(self, exception):
        is_catchable = any(
            exc in self.catch_exceptions
            for exc in [type(exception), exception]
        )
        logger.debug('Testing if {} is catcheable:{}'.format(
            type(exception),
            is_catchable
        ))
        return is_catchable

    def _exceeded_max_failures(self, total_failures):
        return total_failures >= self.max_failures

    def _raise_openess(self):
        logger.critical(
            'Open circuit for {failure_key} {cicuit_storage_key}'.format(
                failure_key=self.failure_key,
                cicuit_storage_key=self.circuit_key
            )
        )
        raise self.max_failure_exception
