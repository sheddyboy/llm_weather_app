"""LLM briefing: a narrative summary generated from a stored record's weather.

A single structured OpenAI call (via LangChain v1's
``ChatOpenAI(...).with_structured_output(BriefingResponse)``) transforms data that
has already been fetched into a short briefing, not an agent loop (ARCHITECTURE
§6). The result is cache-first against the :class:`CacheBackend`, but unlike the
time-based provider caches the key is a *fingerprint* (SHA-256) of the record's
weather + AQI data: a briefing therefore stays cached until the underlying record
changes, at which point the fingerprint, and so the key, changes (ARCHITECTURE
§7). This is cost-driven, OpenAI calls are the most expensive in the system.

The structured runnable is injectable so tests can drive a fake model without
hitting OpenAI; in production it is built lazily from settings. Any failure of the
LLM call surfaces as :class:`ExternalAPIQuotaExceededError` rather than leaking a
raw provider exception (ARCHITECTURE §8).
"""

import hashlib
import json
from typing import Any

from app.core.cache import CacheBackend
from app.core.config import settings
from app.core.logging import logger
from app.exceptions import ExternalAPIQuotaExceededError
from app.schemas.briefing import BriefingResponse
from app.schemas.records import WeatherRecordRead

BRIEFING_TTL = 30 * 24 * 3600  # 30 days; key is a data fingerprint, so this is a cap

_SYSTEM_PROMPT = (
    "You are a concise weather assistant. Given a location and its daily weather "
    "readings over a date range, write a short, practical briefing. Base every "
    "statement only on the data provided; do not invent values."
)


class BriefingService:
    """Cache-first, structured LLM briefing for a weather record."""

    def __init__(
        self,
        cache: CacheBackend,
        *,
        api_key: str | None = None,
        model: str | None = None,
        llm: Any | None = None,
    ) -> None:
        self._cache = cache
        self._api_key = api_key if api_key is not None else settings.openai_api_key
        self._model = model if model is not None else settings.openai_model
        # An optional pre-built structured runnable (returns BriefingResponse from
        # ``ainvoke``); injected by tests, lazily built from settings otherwise.
        self._llm = llm

    async def generate_briefing(self, record: WeatherRecordRead) -> BriefingResponse:
        """Return a briefing for ``record`` (cache-first on a data fingerprint)."""
        key = f"briefing:{_fingerprint(record)}"
        cached = await self._cache.get(key)
        if cached is not None:
            logger.debug("Briefing cache hit for {}", key)
            return BriefingResponse.model_validate(cached)
        logger.debug("Briefing cache miss for {}", key)

        briefing = await self._invoke(record)
        await self._cache.set(key, briefing.model_dump(), ttl=BRIEFING_TTL)
        return briefing

    async def _invoke(self, record: WeatherRecordRead) -> BriefingResponse:
        llm = self._build_llm()
        messages = [
            ("system", _SYSTEM_PROMPT),
            ("human", _render_prompt(record)),
        ]
        try:
            return await llm.ainvoke(messages)
        except Exception as exc:  # noqa: BLE001 - normalize any LLM/transport error
            logger.warning("Briefing generation failed: {}", exc)
            raise ExternalAPIQuotaExceededError(
                "The OpenAI API is unavailable or its quota has been reached."
            ) from exc

    def _build_llm(self) -> Any:
        if self._llm is not None:
            return self._llm
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=self._model, api_key=self._api_key, temperature=0
        ).with_structured_output(BriefingResponse)


def _fingerprint(record: WeatherRecordRead) -> str:
    """A stable SHA-256 over the weather + AQI data that drives the briefing."""
    payload = {
        "location": record.location.resolved_name,
        "start": record.start_date.isoformat(),
        "end": record.end_date.isoformat(),
        "readings": [
            {
                "date": r.date.isoformat(),
                "temp_min": str(r.temp_min),
                "temp_max": str(r.temp_max),
                "conditions": r.conditions,
                "aqi": r.aqi,
            }
            for r in record.readings
        ],
    }
    blob = json.dumps(payload, sort_keys=True)
    return hashlib.sha256(blob.encode()).hexdigest()


def _render_prompt(record: WeatherRecordRead) -> str:
    """Render the record's data into the human prompt for the model."""
    lines = [
        f"Location: {record.location.resolved_name}",
        f"Date range: {record.start_date.isoformat()} to "
        f"{record.end_date.isoformat()}",
        "Daily readings:",
    ]
    if record.readings:
        for r in record.readings:
            aqi = "n/a" if r.aqi is None else str(r.aqi)
            lines.append(
                f"- {r.date.isoformat()}: {r.temp_min}C to {r.temp_max}C, "
                f"{r.conditions}, AQI {aqi}"
            )
    else:
        lines.append("- (no daily readings available)")
    return "\n".join(lines)


__all__ = ["BriefingService", "BRIEFING_TTL"]
