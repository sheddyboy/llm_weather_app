"""Pluggable cache layer (ARCHITECTURE §7).

Calling code (the service layer, from batch 7 onwards) only ever talks to the
abstract `CacheBackend` interface, never to a concrete backend. The local backend
is `InMemoryCache` (cachetools, async-safe); `RedisCache` (redis.asyncio) is the
deployment backend, swapped in via `CACHE_BACKEND=redis` (set in docker-compose).

Per the architecture's TTL table, different data types use very different TTLs
(current weather ~15 min, YouTube results up to 30 days), so `set` takes a
per-call `ttl`. `InMemoryCache` therefore tracks an absolute expiry per key and
uses the `cachetools.TTLCache` purely as a bounded, LRU-evicting store (its own
expiry disabled with `ttl=inf`), keeping expiry exact regardless of the mix.
"""

import asyncio
import json
import math
import time
from abc import ABC, abstractmethod
from collections.abc import Callable
from functools import lru_cache
from typing import Any

import redis.asyncio as aioredis
from cachetools import TTLCache

from app.core.config import settings
from app.core.logging import logger

DEFAULT_TTL = 900  # 15 minutes, the shortest TTL in the architecture's table
DEFAULT_MAXSIZE = 1024


class CacheBackend(ABC):
    """Abstract async cache interface; the only type calling code depends on."""

    @abstractmethod
    async def get(self, key: str) -> Any | None:
        """Return the cached value for `key`, or `None` if missing/expired."""

    @abstractmethod
    async def set(self, key: str, value: Any, ttl: float | None = None) -> None:
        """Store `value` under `key`, expiring after `ttl` seconds."""

    @abstractmethod
    async def delete(self, key: str) -> None:
        """Remove `key` from the cache; a no-op if it is absent."""


class InMemoryCache(CacheBackend):
    """In-memory cache for local development, backed by `cachetools.TTLCache`.

    Async-safety is provided by an `asyncio.Lock` around every mutation, since
    the underlying cache is not concurrency-safe. Expiry is tracked per key as an
    absolute deadline so heterogeneous TTLs coexist correctly.
    """

    def __init__(
        self,
        maxsize: int = DEFAULT_MAXSIZE,
        default_ttl: float = DEFAULT_TTL,
        timer: Callable[[], float] = time.monotonic,
    ) -> None:
        self._default_ttl = default_ttl
        self._timer = timer
        # ttl=inf: the store never expires entries itself; we manage per-key
        # expiry manually so each key can carry its own TTL. It still bounds
        # memory via `maxsize` and evicts least-recently-used entries.
        self._store: TTLCache = TTLCache(maxsize=maxsize, ttl=math.inf, timer=timer)
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Any | None:
        async with self._lock:
            item = self._store.get(key)
            if item is None:
                return None
            value, expire_at = item
            if self._timer() >= expire_at:
                del self._store[key]
                return None
            return value

    async def set(self, key: str, value: Any, ttl: float | None = None) -> None:
        ttl = self._default_ttl if ttl is None else ttl
        async with self._lock:
            self._store[key] = (value, self._timer() + ttl)

    async def delete(self, key: str) -> None:
        async with self._lock:
            self._store.pop(key, None)


class RedisCache(CacheBackend):
    """Deployment cache backed by Redis (redis.asyncio), used under Docker.

    Values are JSON-serialized so the same dict payloads the services cache
    locally round-trip identically through Redis. Per-key expiry uses Redis's
    native `EX` (whole seconds, rounded up), so the architecture's heterogeneous
    TTLs are honored by Redis itself. The client is created lazily from the URL on
    first use, or injected directly (tests pass a fake client); either way it is
    decoded so values come back as `str`.
    """

    def __init__(
        self,
        redis_url: str,
        default_ttl: float = DEFAULT_TTL,
        *,
        client: aioredis.Redis | None = None,
    ) -> None:
        self._redis_url = redis_url
        self._default_ttl = default_ttl
        self._client = client

    def _get_client(self) -> aioredis.Redis:
        if self._client is None:
            self._client = aioredis.from_url(self._redis_url, decode_responses=True)
        return self._client

    async def get(self, key: str) -> Any | None:
        raw = await self._get_client().get(key)
        return None if raw is None else json.loads(raw)

    async def set(self, key: str, value: Any, ttl: float | None = None) -> None:
        ttl = self._default_ttl if ttl is None else ttl
        # Redis EX takes whole seconds; round up so a key never expires early.
        await self._get_client().set(key, json.dumps(value), ex=math.ceil(ttl))

    async def delete(self, key: str) -> None:
        await self._get_client().delete(key)


@lru_cache
def get_cache() -> CacheBackend:
    """Return the process-wide cache backend selected by `CACHE_BACKEND`."""
    backend = settings.cache_backend.lower()
    if backend == "memory":
        logger.debug("Using in-memory cache backend")
        return InMemoryCache()
    if backend == "redis":
        logger.debug("Using Redis cache backend")
        return RedisCache(settings.redis_url)
    raise ValueError(f"Unknown CACHE_BACKEND: {settings.cache_backend!r}")


__all__ = [
    "CacheBackend",
    "InMemoryCache",
    "RedisCache",
    "get_cache",
]
