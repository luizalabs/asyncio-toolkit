import pytest

from asyncio_toolkit.circuit_breaker.storage import (
    CircuitBreakerStorageAdapter,
    MemcachedStorageAdapter,
    RedisPoolStorageAdapter,
    RedisStorageAdapter,
    SimpleCacheStorageAdapter
)


class FakeStorage():
    pass


class TestCircuitBreakerStorageAdapter:

    @pytest.fixture
    def simple_storage_adapter(self, simple_cache):
        return CircuitBreakerStorageAdapter(simple_cache)

    @pytest.fixture
    def memcached_storage_adapter(self, memcached):
        return CircuitBreakerStorageAdapter(memcached)

    @pytest.fixture
    def redis_storage_adapter(self, redis):
        return CircuitBreakerStorageAdapter(redis)

    @pytest.fixture
    def redis_pool_storage_adapter(self, redis_pool):
        return CircuitBreakerStorageAdapter(redis_pool)

    @pytest.mark.parametrize(
        'adapter_fixture, expected', [
            ('simple_storage_adapter', SimpleCacheStorageAdapter),
            ('memcached_storage_adapter', MemcachedStorageAdapter),
            ('redis_storage_adapter', RedisStorageAdapter),
            ('redis_pool_storage_adapter', RedisPoolStorageAdapter),
        ]
    )
    def test_should_init_adapter_correctly(self, request, adapter_fixture, expected):
        adapter = request.getfuncargvalue(adapter_fixture)
        assert type(adapter._storage) == expected

    @pytest.mark.parametrize(
        'storage', [
            (FakeStorage(), ),
            (None, )
        ]
    )
    def test_should_raise_exception_when_init_with_invalid_storage(
        self,
        storage
    ):
        with pytest.raises(Exception):
            CircuitBreakerStorageAdapter(storage)
