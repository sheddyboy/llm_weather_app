"""Shared pytest fixtures for database-backed tests.

Tests run against a dedicated Postgres database (`DATABASE_URL_TEST`), separate
from the dev database (ARCHITECTURE §9). Alembic migrations are applied once per
session and torn down afterwards. Each test runs inside an outer transaction that
is rolled back at the end, so tests stay isolated without rebuilding schema state
per test; `session.commit()` inside a test commits to a savepoint, preserving the
outer rollback.
"""

from collections.abc import AsyncIterator, Iterator

import pytest
import pytest_asyncio
from alembic.config import Config
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from alembic import command
from app.core.config import settings

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
