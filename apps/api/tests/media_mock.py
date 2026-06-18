"""Mock transports for the YouTube and Places enrichment endpoints.

External HTTP is mocked at the transport layer (ARCHITECTURE §9): each handler
returns a canned payload (or a chosen error status) and counts calls, so cache
hit/miss and graceful-degradation behavior can be asserted end to end without
spending real quota or needing billing.
"""

from collections import Counter

import httpx

YOUTUBE_RESPONSE = {
    "items": [
        {
            "id": {"videoId": "abc123"},
            "snippet": {
                "title": "London travel guide",
                "channelTitle": "Travel Channel",
                "thumbnails": {"medium": {"url": "https://i.ytimg.com/abc123.jpg"}},
            },
        },
        {
            "id": {"videoId": "def456"},
            "snippet": {
                "title": "London weather explained",
                "channelTitle": "Weather Channel",
                "thumbnails": {"default": {"url": "https://i.ytimg.com/def456.jpg"}},
            },
        },
    ]
}

PLACES_RESPONSE = {
    "places": [
        {
            "displayName": {"text": "British Museum"},
            "formattedAddress": "Great Russell St, London",
            "types": ["museum", "tourist_attraction"],
            "rating": 4.7,
        },
        {
            "displayName": {"text": "Hyde Park"},
            "formattedAddress": "London",
            "types": ["park"],
            "rating": 4.6,
        },
    ]
}


class YouTubeMock:
    """MockTransport handler for the YouTube `search.list` endpoint."""

    def __init__(self, *, response: dict | None = None, status: int = 200) -> None:
        self.response = response if response is not None else YOUTUBE_RESPONSE
        self.status = status
        self.calls: Counter[str] = Counter()

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.calls[request.url.path] += 1
        return httpx.Response(self.status, json=self.response)


class PlacesMock:
    """MockTransport handler for the Places Nearby Search endpoint."""

    def __init__(self, *, response: dict | None = None, status: int = 200) -> None:
        self.response = response if response is not None else PLACES_RESPONSE
        self.status = status
        self.calls: Counter[str] = Counter()

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.calls[request.url.path] += 1
        return httpx.Response(self.status, json=self.response)
