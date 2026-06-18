"""Shared pytest fixtures for database-backed tests.

Tests run against a dedicated Postgres database (`DATABASE_URL_TEST`), separate
from the dev database (ARCHITECTURE §9). Alembic migrations are applied once per
session and torn down afterwards. Each test runs inside an outer transaction that
is rolled back at the end, so tests stay isolated without rebuilding schema state
per test; `session.commit()` inside a test commits to a savepoint, preserving the
outer rollback.
"""

from collections.abc import AsyncIterator, Callable, Iterator

import httpx
import pytest
import pytest_asyncio
from alembic.config import Config
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from alembic import command
from app.core.cache import InMemoryCache
from app.core.config import settings
from app.core.database import get_db
from app.dependencies import get_geocoding_service, get_weather_provider
from app.main import app
from app.repositories import WeatherRepository
from app.services import GeocodingService, WeatherProvider

TEST_DATABASE_URL = settings.database_url_test


@pytest.fixture(scope="session")
def alembic_config() -> Config:
    """Alembic config pointed at the test database."""
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", TEST_DATABASE_URL)
    return cfg


@pytest.fixture(scope="session", autouse=True)
def migrated_test_db(alembic_config: Config) -> Iterator[None]:
    """Migrate the test database to head once per session, downgrade after."""
    command.upgrade(alembic_config, "head")
    yield
    command.downgrade(alembic_config, "base")


@pytest_asyncio.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    """Yield an AsyncSession wrapped in a transaction that is rolled back.

    A fresh engine is created per test so the connection is bound to the test's
    own event loop (pytest-asyncio uses a function-scoped loop by default).
    """
    engine = create_async_engine(TEST_DATABASE_URL, future=True, poolclass=NullPool)
    async with engine.connect() as connection:
        transaction = await connection.begin()
        session = AsyncSession(
            bind=connection,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )
        try:
            yield session
        finally:
            await session.close()
            if transaction.is_active:
                await transaction.rollback()
    await engine.dispose()


@pytest_asyncio.fixture
async def api_client(
    db_session: AsyncSession,
) -> AsyncIterator[Callable[..., httpx.AsyncClient]]:
    """Yield a factory building an ASGI test client wired to mocks.

    The factory takes an OpenWeatherMap mock handler and returns an
    :class:`httpx.AsyncClient` driving the real FastAPI app, with the service and
    session dependencies overridden so every request runs against the rolled-back
    test session and the mocked transport (no real HTTP, no real DB writes). The
    geocoding service and weather provider share one mock client and the provider
    keeps a single in-memory cache across requests, so cache behavior is realistic.
    """
    created: list[tuple[httpx.AsyncClient, httpx.AsyncClient]] = []

    def factory(handler) -> httpx.AsyncClient:
        mock_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        cache = InMemoryCache()

        app.dependency_overrides[get_db] = lambda: db_session
        app.dependency_overrides[get_geocoding_service] = lambda: GeocodingService(
            WeatherRepository(db_session), api_key="test-key", client=mock_client
        )
        app.dependency_overrides[get_weather_provider] = lambda: WeatherProvider(
            cache, api_key="test-key", client=mock_client
        )

        ac = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        )
        created.append((ac, mock_client))
        return ac

    try:
        yield factory
    finally:
        for ac, mock_client in created:
            await ac.aclose()
            await mock_client.aclose()
        app.dependency_overrides.clear()
