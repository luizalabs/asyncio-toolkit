import logging

from .base import BaseCircuitBreaker

logger = logging.getLogger(__name__)


class CircuitBreaker(BaseCircuitBreaker):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def increment(self):
        """
        This method demands that the implementation is responsible for
        getting a storage key from the storage engine.
        """
        total = self.storage.increment(self.failure_key)

        logger.info(
            'Increase failure for: {key} - '
            'max failures {max_failures} - '
            'total {total}'.format(
                key=self.failure_key,
                max_failures=self.max_failures,
                total=total
            )
        )

        return int(total or 0)

    @property
    def is_circuit_open(self):
        return self.storage.get(self.circuit_key) or False

    def open_circuit(self):
        self.storage.set(
            self.circuit_key,
            1,
            self.circuit_timeout
        )

    def __enter__(self):
        self._check_circuit()

        return self

    def _check_circuit(self):
        if self.is_circuit_open:
            self._raise_openess()

    def __exit__(self, exc_type, exc_value, traceback):
        if self._is_catchable(exc_type):
            self._check_circuit()

            total_failures = self.increment()

            if self._exceeded_max_failures(total_failures):
                self.open_circuit()

                logger.info(
                    'Max failures exceeded by: {}'.format(
                        self.failure_key
                    )
                )

                raise self.max_failure_exception
