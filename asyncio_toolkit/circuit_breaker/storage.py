import abc
import asyncio

from aiomcache.client import Client as AiomClient
from aioredis.commands import Redis
from aioredis.pool import RedisPool
from werkzeug.contrib.cache import SimpleCache


class CircuitBreakerBaseStorage(metaclass=abc.ABCMeta):

    @abc.abstractmethod
    def get(self, key):
        """
        This method must implement a GET call to a stored value.
        It should return an int value that represents how many times
        this single key has been set.
        """

    @abc.abstractmethod
    def incr(self, key, timeout):
        """
        This method must increment 1 int value based in a key stored value.
        It should return an int value that represents how many times
        this single key has been set, after it was incremented by its request.
        """

    @abc.abstractmethod
    def set(self, key, value, timeout):
        """
        This method must add a key with an int value and set a ttl to it
        """


class SimpleCacheStorageAdapter(CircuitBreakerBaseStorage):

    def __init__(self, storage):
        self._storage = storage

    def get(self, key):
        return self._storage.get(key)

    def incr(self, key, timeout):
        self._storage.add(key, 0, timeout)
        return self._storage.inc(key)

    def set(self, key, value, timeout):
        return self._storage.set(key, value, timeout)


class MemcachedStorageAdapter(CircuitBreakerBaseStorage):

    def __init__(self, storage):
        self._storage = storage

    @asyncio.coroutine
    def get(self, key):
        value = yield from self._storage.get(
            key.encode('utf-8')
        )
        return value.decode('utf-8') if value else None

    @asyncio.coroutine
    def incr(self, key, timeout):
        yield from self._storage.add(
            key.encode('utf-8'),
            '0'.encode('utf-8'),
            timeout
        )
        return (yield from self._storage.incr(
            key.encode('utf-8'))
        )

    @asyncio.coroutine
    def set(self, key, value, timeout):
        yield from self._storage.set(
            key.encode('utf-8'),
            bytes(value),
            timeout
        )


class RedisStorageAdapter(CircuitBreakerBaseStorage):

    def __init__(self, storage):
        self._storage = storage

    @asyncio.coroutine
    def get(self, key):
        return (yield from self._storage.get(key))

    @asyncio.coroutine
    def incr(self, key, timeout):
        value = yield from self._storage.incr(key)
        yield from self._storage.expire(key, timeout)
        return value

    @asyncio.coroutine
    def set(self, key, value, timeout):
        yield from self._storage.set(key, value, expire=timeout)


class RedisPoolStorageAdapter(CircuitBreakerBaseStorage):

    def __init__(self, storage):
        self._storage = storage

    @asyncio.coroutine
    def get(self, key):
        with (yield from self._storage) as redis:
            return (yield from redis.get(key))

    @asyncio.coroutine
    def incr(self, key, timeout):
        with (yield from self._storage) as redis:
            value = yield from redis.incr(key)
            yield from redis.expire(key, timeout)
            return value

    @asyncio.coroutine
    def set(self, key, value, timeout):
        with (yield from self._storage) as redis:
            yield from redis.set(key, value, expire=timeout)


class CircuitBreakerStorageAdapter(CircuitBreakerBaseStorage):

    def __init__(self, storage):
        if type(storage) == SimpleCache:
            self._storage = SimpleCacheStorageAdapter(storage)
        elif type(storage) == AiomClient:
            self._storage = MemcachedStorageAdapter(storage)
        elif type(storage) == Redis:
            self._storage = RedisStorageAdapter(storage)
        elif type(storage) == RedisPool:
            self._storage = RedisPoolStorageAdapter(storage)
        else:
            raise Exception('Invalid storaged: {}'.format(type(storage)))

    def get(self, key):
        return self._storage.get(key)

    def incr(self, key, timeout):
        return self._storage.incr(key, timeout)

    def set(self, key, value, timeout):
        return self._storage.set(key, value, timeout)
