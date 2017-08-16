import logging
from functools import wraps

from .base import BaseCircuitBreaker

logger = logging.getLogger(__name__)


class circuit_breaker(BaseCircuitBreaker):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def increment(self):
        """
        This method demands that the implementation is responsible for
        getting a storage key from the storage engine.
        """

        key = self.failure_key.encode('utf-8')

        await self.storage.add(
            key,
            '0'.encode('utf-8'),
            self.max_failure_timeout
        )
        total = await self.storage.incr(key)

        logger.info(
            'Increase failure for: {key} - '
            'max failures {max_failures} - '
            'total {total}'.format(
                key=self.failure_key,
                max_failures=self.max_failures,
                total=total
            )
        )

        return (await self.storage.get(key) or 0)

    @property
    async def is_circuit_open(self):
        is_open = await self.storage.get(self.circuit_key) or False
        return is_open

    async def open_circuit(self):
        await self.storage.set(
            self.circuit_key,
            bytes(True),
            self.circuit_timeout
        )

    async def _check_circuit(self):
        is_open = await self.is_circuit_open
        if is_open:
            self._raise_openess()

    def __call__(self, method):
        @wraps(method)
        async def wrapper(obj, *args, **kwargs):
            await self._check_circuit()

            try:
                return (await method(obj, *args, **kwargs))
            except Exception as e:
                if self._is_catchable(e):
                    await self._check_circuit()

                    total_failures = await self.increment()

                    if self._exceeded_max_failures(total_failures):
                        await self.open_circuit()

                        logger.info(
                            'Max failures exceeded by: {}'.format(
                                self.failure_key
                            )
                        )

                        raise self.max_failure_exception
        return wrapper
