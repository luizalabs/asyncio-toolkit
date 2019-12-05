import time

from asyncio_toolkit.circuit_breaker.storage import MemoryStorage


class TestMemoryStorage:

    def test_get_found(self):
        storage = MemoryStorage()
        key = 'some_key'
        value = 'some_data'
        storage.set(key, value, 2)
        result = storage.get(key)
        assert result == value

    def test_get_not_found(self):
        storage = MemoryStorage()
        result = storage.get('some_key')
        assert result is None

    def test_get_timeout_exceeded(self):
        storage = MemoryStorage()
        key = 'some_key'
        storage.set(key, 'some_data', 2)
        storage._timeout = {key: time.time() - 1}
        result = storage.get(key)
        assert result is None

    def test_increment(self):
        storage = MemoryStorage()
        key = 'some_key'
        storage.increment(key)
        result = storage.get(key)
        assert result == 1

    def test_set(self):
        storage = MemoryStorage()
        key = 'some_key'
        value = 'some_data'
        storage.set(key, value, 2)
        result = storage.get(key)
        assert result == value

    def test_expire(self):
        storage = MemoryStorage()
        key = 'some_key'
        storage.expire(key, 2)
        assert key in storage._timeout

    def test_expire_with_none_timeout(self):
        storage = MemoryStorage()
        key = 'some_key'
        storage.expire(key, None)
        assert not storage._timeout
