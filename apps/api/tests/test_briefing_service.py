"""Batch 11: unit tests for the LLM briefing service.

These exercise the service against a real :class:`InMemoryCache` with the OpenAI
call replaced by a fake structured runnable, proving: a miss invokes the model and
caches the result, a second request for the same data is served from cache without
re-invoking, a change to the record's data busts the fingerprint-based key, and an
LLM failure is normalized to :class:`ExternalAPIQuotaExceededError`.
"""

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from app.core.cache import InMemoryCache
from app.exceptions import ExternalAPIQuotaExceededError
from app.schemas.records import (
    DailyReadingRead,
    LocationRead,
    WeatherRecordRead,
)
from app.services.briefing_service import BRIEFING_TTL, BriefingService
from tests.briefing_mock import FailingBriefingLLM, FakeBriefingLLM


def _record(*, temp_max: str = "20.0", aqi: int | None = 1) -> WeatherRecordRead:
    now = datetime.now(UTC)
    location = LocationRead(
        id=uuid.uuid4(),
        query_text="London",
        resolved_name="London, England, GB",
        latitude=Decimal("51.5074"),
        longitude=Decimal("-0.1278"),
        country="GB",
        created_at=now,
    )
    reading = DailyReadingRead(
        id=uuid.uuid4(),
        date=date(2026, 6, 18),
        temp_min=Decimal("12.0"),
        temp_max=Decimal(temp_max),
        conditions="Clear",
        aqi=aqi,
    )
    return WeatherRecordRead(
        id=uuid.uuid4(),
        location=location,
        start_date=date(2026, 6, 18),
        end_date=date(2026, 6, 18),
        created_at=now,
        updated_at=now,
        readings=[reading],
    )


async def test_generate_briefing_invokes_llm_and_returns_response() -> None:
    llm = FakeBriefingLLM()
    service = BriefingService(InMemoryCache(), llm=llm)

    result = await service.generate_briefing(_record())

    assert result == llm.response
    assert len(llm.calls) == 1


async def test_briefing_is_cached_across_requests() -> None:
    llm = FakeBriefingLLM()
    service = BriefingService(InMemoryCache(), llm=llm)
    record = _record()

    first = await service.generate_briefing(record)
    second = await service.generate_briefing(record)

    assert first == second
    assert len(llm.calls) == 1  # second request served from cache


async def test_changed_record_data_busts_the_cache() -> None:
    llm = FakeBriefingLLM()
    service = BriefingService(InMemoryCache(), llm=llm)

    await service.generate_briefing(_record(temp_max="20.0"))
    await service.generate_briefing(_record(temp_max="25.0"))

    assert len(llm.calls) == 2  # different data fingerprint -> different key


async def test_identical_data_on_a_different_record_hits_cache() -> None:
    # The key is a fingerprint of the weather data, not the record id, so two
    # records with identical data and location share a cached briefing.
    llm = FakeBriefingLLM()
    cache = InMemoryCache()
    service = BriefingService(cache, llm=llm)

    await service.generate_briefing(_record())
    await service.generate_briefing(_record())  # new id, same data

    assert len(llm.calls) == 1


async def test_llm_failure_is_normalized() -> None:
    llm = FailingBriefingLLM()
    service = BriefingService(InMemoryCache(), llm=llm)

    with pytest.raises(ExternalAPIQuotaExceededError):
        await service.generate_briefing(_record())

    assert llm.calls == 1


async def test_failed_briefing_is_not_cached() -> None:
    llm = FailingBriefingLLM()
    service = BriefingService(InMemoryCache(), llm=llm)
    record = _record()

    with pytest.raises(ExternalAPIQuotaExceededError):
        await service.generate_briefing(record)
    with pytest.raises(ExternalAPIQuotaExceededError):
        await service.generate_briefing(record)

    assert llm.calls == 2  # nothing cached, so the second attempt re-invokes


def test_briefing_ttl_is_long() -> None:
    assert BRIEFING_TTL == 30 * 24 * 3600
