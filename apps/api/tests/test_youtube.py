"""Batch 10: the cache-first, flag-gated YouTube enrichment service.

External HTTP is mocked at the transport layer (ARCHITECTURE §9). The recorder
counts requests so cache hit/miss is observable, and the ``enabled`` flag is
exercised in both modes to prove the safety toggle works: live mode parses real
responses, stub mode returns canned data without any HTTP call.
"""

import httpx
import pytest

from app.core.cache import InMemoryCache
from app.exceptions import ExternalAPIQuotaExceededError
from app.services.youtube import YOUTUBE_TTL, YouTubeService
from tests.media_mock import YOUTUBE_RESPONSE


class Recorder:
    """A MockTransport handler that counts requests and can fail on demand."""

    def __init__(self, *, status: int = 200, response: dict | None = None) -> None:
        self.status = status
        self.response = response if response is not None else YOUTUBE_RESPONSE
        self.count = 0

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.count += 1
        return httpx.Response(self.status, json=self.response)


def _service(recorder: Recorder, *, enabled: bool = True) -> YouTubeService:
    client = httpx.AsyncClient(transport=httpx.MockTransport(recorder))
    return YouTubeService(
        InMemoryCache(), api_key="test-key", enabled=enabled, client=client
    )


async def test_live_mode_parses_videos() -> None:
    service = _service(Recorder())

    videos = await service.search_videos("London")

    assert len(videos) == 2
    first = videos[0]
    assert first["video_id"] == "abc123"
    assert first["title"] == "London travel guide"
    assert first["channel"] == "Travel Channel"
    assert first["url"] == "https://www.youtube.com/watch?v=abc123"
    assert first["thumbnail"] == "https://i.ytimg.com/abc123.jpg"
    # The second item falls back to the default thumbnail.
    assert videos[1]["thumbnail"] == "https://i.ytimg.com/def456.jpg"


async def test_cache_hit_skips_second_call() -> None:
    recorder = Recorder()
    service = _service(recorder)

    await service.search_videos("London")
    await service.search_videos("London")

    assert recorder.count == 1


async def test_cache_key_is_case_insensitive() -> None:
    recorder = Recorder()
    service = _service(recorder)

    await service.search_videos("London")
    await service.search_videos("  london  ")

    assert recorder.count == 1


async def test_stub_mode_returns_data_without_http() -> None:
    recorder = Recorder()
    service = _service(recorder, enabled=False)

    videos = await service.search_videos("London")

    assert recorder.count == 0
    assert len(videos) == 1
    assert videos[0]["video_id"] == "stub-youtube"
    assert "London" in videos[0]["title"]


async def test_http_failure_raises_quota_error() -> None:
    service = _service(Recorder(status=403))

    with pytest.raises(ExternalAPIQuotaExceededError):
        await service.search_videos("London")


async def test_failed_call_is_not_cached() -> None:
    recorder = Recorder(status=403)
    service = _service(recorder)

    with pytest.raises(ExternalAPIQuotaExceededError):
        await service.search_videos("London")
    with pytest.raises(ExternalAPIQuotaExceededError):
        await service.search_videos("London")

    assert recorder.count == 2


def test_ttl_is_multi_day() -> None:
    assert YOUTUBE_TTL >= 24 * 3600
