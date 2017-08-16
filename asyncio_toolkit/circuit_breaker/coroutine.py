import asyncio
import logging
from functools import wraps

from .base import BaseCircuitBreaker

logger = logging.getLogger(__name__)


class circuit_breaker(BaseCircuitBreaker):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @asyncio.coroutine
    def increment(self):
        """
        This method demands that the implementation is responsible for
        getting a storage key from the storage engine.
        """

        key = self.failure_key.encode('utf-8')

        yield from self.storage.add(
            key,
            '0'.encode('utf-8'),
            self.max_failure_timeout
        )
        total = yield from self.storage.incr(key)

        logger.info(
            'Increase failure for: {key} - '
            'max failures {max_failures} - '
            'total {total}'.format(
                key=self.failure_key,
                max_failures=self.max_failures,
                total=total
            )
        )

        return (yield from self.storage.get(key) or 0)

    @property
    @asyncio.coroutine
    def is_circuit_open(self):
        is_open = yield from self.storage.get(self.circuit_key) or False
        return is_open

    @asyncio.coroutine
    def open_circuit(self):
        yield from self.storage.set(
            self.circuit_key,
            bytes(True),
            self.circuit_timeout
        )

    @asyncio.coroutine
    def _check_circuit(self):
        is_open = yield from self.is_circuit_open
        if is_open:
            self._raise_openess()

    def __call__(self, method):
        @asyncio.coroutine
        @wraps(method)
        def wrapper(obj, *args, **kwargs):
            yield from self._check_circuit()

            try:
                return (yield from method(obj, *args, **kwargs))
            except Exception as e:
                if self._is_catchable(e):
                    yield from self._check_circuit()

                    total_failures = yield from self.increment()

                    if self._exceeded_max_failures(total_failures):
                        yield from self.open_circuit()

                        logger.info(
                            'Max failures exceeded by: {}'.format(
                                self.failure_key
                            )
                        )

                        raise self.max_failure_exception
        return wrapper
