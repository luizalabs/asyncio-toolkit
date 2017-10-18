import logging

from .coroutine import circuit_breaker as coroutine_circuit_breaker

logger = logging.getLogger(__name__)


class circuit_breaker(coroutine_circuit_breaker):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def increment(self):
        return await super().increment()

    async def open_circuit(self):
        await super().open_circuit()

    async def _check_circuit(self):
        await super()._check_circuit()
