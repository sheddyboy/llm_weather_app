"""The cache abstraction: set/get/delete/expiry plus backend selection."""

import pytest

from app.core.cache import (
    CacheBackend,
    InMemoryCache,
    RedisCache,
    get_cache,
)


class FakeClock:
    """Manually advanceable monotonic clock so expiry is testable without sleep."""

    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


async def test_set_then_get_returns_value() -> None:
    cache = InMemoryCache()
    await cache.set("k", {"v": 1})
    assert await cache.get("k") == {"v": 1}


async def test_get_missing_key_returns_none() -> None:
    cache = InMemoryCache()
    assert await cache.get("absent") is None


async def test_set_overwrites_existing_value() -> None:
    cache = InMemoryCache()
    await cache.set("k", "first")
    await cache.set("k", "second")
    assert await cache.get("k") == "second"


async def test_delete_removes_key() -> None:
    cache = InMemoryCache()
    await cache.set("k", "v")
    await cache.delete("k")
    assert await cache.get("k") is None


async def test_delete_missing_key_is_noop() -> None:
    cache = InMemoryCache()
    await cache.delete("absent")  # must not raise


async def test_value_expires_after_ttl() -> None:
    clock = FakeClock()
    cache = InMemoryCache(timer=clock)
    await cache.set("k", "v", ttl=10)

    clock.advance(9)
    assert await cache.get("k") == "v"  # still within TTL

    clock.advance(1)  # now at exactly the deadline
    assert await cache.get("k") is None


async def test_per_key_ttls_are_independent() -> None:
    clock = FakeClock()
    cache = InMemoryCache(timer=clock)
    await cache.set("short", "s", ttl=10)
    await cache.set("long", "l", ttl=100)

    clock.advance(20)
    assert await cache.get("short") is None
    assert await cache.get("long") == "l"


async def test_default_ttl_used_when_unspecified() -> None:
    clock = FakeClock()
    cache = InMemoryCache(default_ttl=30, timer=clock)
    await cache.set("k", "v")

    clock.advance(29)
    assert await cache.get("k") == "v"
    clock.advance(1)
    assert await cache.get("k") is None


async def test_maxsize_evicts_when_full() -> None:
    cache = InMemoryCache(maxsize=2)
    await cache.set("a", 1)
    await cache.set("b", 2)
    await cache.set("c", 3)  # evicts the least-recently-used entry
    present = [k for k in ("a", "b", "c") if await cache.get(k) is not None]
    assert len(present) == 2


def test_get_cache_returns_in_memory_for_memory_backend(monkeypatch) -> None:
    from app.core import cache as cache_module

    monkeypatch.setattr(cache_module.settings, "cache_backend", "memory")
    get_cache.cache_clear()
    backend = get_cache()
    assert isinstance(backend, InMemoryCache)
    assert isinstance(backend, CacheBackend)
    get_cache.cache_clear()


def test_get_cache_returns_redis_for_redis_backend(monkeypatch) -> None:
    from app.core import cache as cache_module

    monkeypatch.setattr(cache_module.settings, "cache_backend", "redis")
    get_cache.cache_clear()
    backend = get_cache()
    assert isinstance(backend, RedisCache)
    get_cache.cache_clear()


def test_get_cache_rejects_unknown_backend(monkeypatch) -> None:
    from app.core import cache as cache_module

    monkeypatch.setattr(cache_module.settings, "cache_backend", "bogus")
    get_cache.cache_clear()
    with pytest.raises(ValueError):
        get_cache()
    get_cache.cache_clear()


def _redis_cache(**kwargs) -> RedisCache:
    """A `RedisCache` backed by an in-process fake Redis (no server needed)."""
    import fakeredis

    client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    return RedisCache("redis://localhost:6379/0", client=client, **kwargs)


async def test_redis_cache_set_get_roundtrips_json() -> None:
    cache = _redis_cache()
    payload = {"temp": 19.5, "conditions": "clear sky", "aqi": 3, "items": [1, 2]}

    await cache.set("weather:london", payload)

    assert await cache.get("weather:london") == payload


async def test_redis_cache_get_missing_returns_none() -> None:
    cache = _redis_cache()
    assert await cache.get("absent") is None


async def test_redis_cache_delete_removes_key() -> None:
    cache = _redis_cache()
    await cache.set("k", {"v": 1})

    await cache.delete("k")

    assert await cache.get("k") is None
    # Deleting an absent key is a no-op.
    await cache.delete("k")


async def test_redis_cache_set_applies_ttl() -> None:
    cache = _redis_cache()
    await cache.set("k", {"v": 1}, ttl=42)

    # The expiry is handed to Redis natively; the fake honors it via EX.
    ttl = await cache._get_client().ttl("k")
    assert 0 < ttl <= 42


async def test_redis_cache_rounds_fractional_ttl_up() -> None:
    cache = _redis_cache()
    await cache.set("k", {"v": 1}, ttl=0.4)

    # math.ceil(0.4) == 1, so the key persists with a 1s TTL rather than expiring
    # immediately from a rounded-down zero.
    assert await cache._get_client().ttl("k") == 1
