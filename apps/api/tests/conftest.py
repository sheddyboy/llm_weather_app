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
from app.dependencies import (
    get_briefing_service,
    get_geocoding_service,
    get_places_service,
    get_weather_provider,
    get_youtube_service,
)
from app.main import app
from app.repositories import WeatherRepository
from app.services import (
    BriefingService,
    GeocodingService,
    PlacesService,
    WeatherProvider,
    YouTubeService,
)

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

    The optional ``youtube``/``places`` handlers (and their ``enable_*`` flags)
    wire the media-enrichment services: pass a mock handler to drive a provider in
    live mode, or set ``enable_*=False`` to exercise the flag-gated stub fallback
    with no HTTP at all. The media services share the provider's cache, so their
    cache behavior is realistic too.

    The optional ``briefing_llm`` is a fake structured runnable injected into the
    briefing service so the OpenAI call is never made; the service still shares the
    same in-memory cache, so its cache-first behavior is exercised realistically.
    """
    clients: list[httpx.AsyncClient] = []

    def factory(
        handler,
        *,
        youtube=None,
        places=None,
        enable_youtube: bool = True,
        enable_places: bool = True,
        briefing_llm=None,
    ) -> httpx.AsyncClient:
        mock_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        clients.append(mock_client)
        cache = InMemoryCache()

        app.dependency_overrides[get_db] = lambda: db_session
        app.dependency_overrides[get_geocoding_service] = lambda: GeocodingService(
            WeatherRepository(db_session), api_key="test-key", client=mock_client
        )
        app.dependency_overrides[get_weather_provider] = lambda: WeatherProvider(
            cache, api_key="test-key", client=mock_client
        )

        if youtube is not None or not enable_youtube:
            yt_client = None
            if youtube is not None:
                yt_client = httpx.AsyncClient(transport=httpx.MockTransport(youtube))
                clients.append(yt_client)
            app.dependency_overrides[get_youtube_service] = lambda: YouTubeService(
                cache, api_key="test-key", enabled=enable_youtube, client=yt_client
            )

        if places is not None or not enable_places:
            pl_client = None
            if places is not None:
                pl_client = httpx.AsyncClient(transport=httpx.MockTransport(places))
                clients.append(pl_client)
            app.dependency_overrides[get_places_service] = lambda: PlacesService(
                cache, api_key="test-key", enabled=enable_places, client=pl_client
            )

        if briefing_llm is not None:
            app.dependency_overrides[get_briefing_service] = lambda: BriefingService(
                cache, api_key="test-key", llm=briefing_llm
            )

        ac = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        )
        clients.append(ac)
        return ac

    try:
        yield factory
    finally:
        for client in clients:
            await client.aclose()
        app.dependency_overrides.clear()
