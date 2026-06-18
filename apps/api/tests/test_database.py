"""Batch 2 plumbing: a session opens against the test database and queries it."""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def test_session_runs_trivial_query(db_session: AsyncSession) -> None:
    result = await db_session.execute(text("SELECT 1"))
    assert result.scalar_one() == 1


async def test_session_targets_the_test_database(db_session: AsyncSession) -> None:
    result = await db_session.execute(text("SELECT current_database()"))
    assert result.scalar_one() == "weatherapp_test"
