"""Async database plumbing: engine, session factory, and the `get_db` dependency.

`DATABASE_URL` is read from the environment from day one (see ARCHITECTURE §10) so
the swap to Docker later is a config change rather than a refactor. Models are
added in batch 3; this module only provides the declarative `Base` they will use
and the session machinery the repository layer depends on.
"""

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


class Base(DeclarativeBase):
    """Declarative base shared by every SQLAlchemy model."""


engine: AsyncEngine = create_async_engine(settings.database_url, future=True)

async_session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency yielding a session, committing on success.

    Rolls back on any exception and always closes the session.
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
