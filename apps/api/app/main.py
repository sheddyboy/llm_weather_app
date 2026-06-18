"""FastAPI application entrypoint.

Batch 1 wires up only the app instance, logging, and a `/health` smoke route.
Routers, database, cache, and the rest are added in later batches.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config import settings
from app.core.logging import configure_logging, logger
from app.exceptions import register_exception_handlers

configure_logging()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    logger.info("{} starting up", settings.meta_name)
    yield
    logger.info("{} shutting down", settings.meta_name)


app = FastAPI(title=settings.meta_name, lifespan=lifespan)
register_exception_handlers(app)


@app.get("/health", tags=["meta"])
async def health() -> dict[str, str]:
    """Liveness probe used by smoke tests and deployment health checks."""
    return {"status": "ok"}
