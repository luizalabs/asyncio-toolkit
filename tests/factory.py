import asyncio

from aiocache import MemcachedCache, RedisCache

from asyncio_toolkit.circuit_breaker.storage import MemoryStorage


def create_memcached_instance():
    return MemcachedCache(
        endpoint='127.0.0.1',
        port=11211,
        loop=asyncio.get_event_loop()
    )


def create_redis_instance():
    return RedisCache(
        endpoint='127.0.0.1',
        port=6379
    )


def create_memory_instance():
    return MemoryStorage()
